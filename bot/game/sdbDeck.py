import json
# from urllib import request
import random
from abc import ABC, abstractmethod

from .. import lib
from .. import botState
from ..cfg import cfg


class SDBCard(ABC):
    def __init__(self, text, url, expansion):
        self.url = url
        self.text = text
        self.expansion = expansion

    def __str__(self):
        return self.url


class BlackCard(SDBCard):
    def __init__(self, text, url, requiredWhiteCards, expansion):
        super().__init__(text, url, expansion)
        self.requiredWhiteCards = requiredWhiteCards


class WhiteCard(SDBCard):
    def __init__(self, text, url, expansion):
        super().__init__(text, url, expansion)
        self.owner = None

    def isOwned(self):
        return self.owner is not None

    def claim(self, player):
        if self.isOwned():
            raise RuntimeError("Attempted to claim a card that is already owned: " + self.text)
        self.owner = player
        self.expansion.ownedWhiteCards += 1

    def revoke(self):
        if not self.isOwned():
            raise RuntimeError("Attempted to revoke a card that is not owned: " + self.text)
        self.owner = None
        self.expansion.ownedWhiteCards -= 1


class SDBExpansion:
    def __init__(self):
        self.white = []
        self.black = []
        self.ownedWhiteCards = 0

    def allOwned(self):
        return self.ownedWhiteCards == len(self.white)


class SDBDeck:
    def __init__(self, metaPath):
        # deckMeta = json.load(request.urlopen(metaUrl))
        deckMeta = lib.jsonHandler.readJSON(metaPath)

        if "expansions" not in deckMeta or deckMeta["expansions"] == {}:
            raise RuntimeError("Attempted to create an empty SDBDeck")

        self.expansionNames = list(deckMeta["expansions"].keys())
        self.cards = {expansion : SDBExpansion() for expansion in self.expansionNames}
        self.name = deckMeta["deck_name"]
        hasWhiteCards = False
        hasBlackCards = False

        for expansion in self.expansionNames:
            if "white" in deckMeta["expansions"][expansion]:
                for cardData in deckMeta["expansions"][expansion]["white"]:
                    self.cards[expansion].white.append(WhiteCard(cardData["text"], cardData["url"]))
            if "black" in deckMeta["expansions"][expansion]:
                for cardData in deckMeta["expansions"][expansion]["black"]:
                    self.cards[expansion].black.append(BlackCard(cardData["text"], cardData["url"], cardData["requiredWhiteCards"]))

            if not hasWhiteCards:
                hasWhiteCards = len(self.cards[expansion].white) != 0
            if not hasBlackCards:
                hasBlackCards = len(self.cards[expansion].black) != 0

        if not hasWhiteCards:
            raise RuntimeError("Attempted to create a deck with no white cards")
        elif not hasBlackCards:
            raise RuntimeError("Attempted to create a deck with no black cards")

        self.emptyBlack = BlackCard("EMPTY", deckMeta["black_back"] if "black_back" in deckMeta else cfg.emptyBlackCard, 0)
        self.emptyWhite = WhiteCard("EMPTY", deckMeta["white_back"] if "white_back" in deckMeta else cfg.emptyWhiteCard)


    def randomWhite(self, expansions=[]):
        if expansions == []:
            expansions = self.expansionNames

        noWhiteCards = True
        for expansion in expansions:
            if len(self.cards[expansion].white) > 1:
                noWhiteCards = False
                break
        if noWhiteCards:
            raise ValueError("No white cards in any of the given expansions: " + ", ".join(expansions))
        
        noFreeCards = True
        for expansion in expansions:
            if not self.cards[expansion].allOwned():
                noFreeCards = False
                break
        if noFreeCards:
            raise ValueError("All white cards are already owned in the given expansions: " + ", ".join(expansions))

        expansion = random.choice(expansions)
        while len(self.cards[expansion].white) == 0 or self.cards[expansion].allOwned():
            expansion = random.choice(expansions)

        card = random.choice(self.cards[expansion].white)
        while card.isOwned():
            card = random.choice(self.cards[expansion].white)

        return card
    

    def randomBlack(self, expansions=[]):
        if expansions == []:
            expansions = self.expansionNames
            
        noBlackCards = True
        for expansion in expansions:
            if len(self.cards[expansion].black) > 1:
                noBlackCards = False
        if noBlackCards:
            raise ValueError("No black cards in any of the given expansions: " + ", ".join(expansions))

        expansion = random.choice(expansions)
        while len(self.cards[expansion].black) == 0:
            expansion = random.choice(expansions)

        return random.choice(self.cards[expansion].black)