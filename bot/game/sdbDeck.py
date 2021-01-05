import json
# from urllib import request
import random
from abc import ABC, abstractmethod

from .. import lib
from .. import botState
from ..cfg import cfg


class SDBCard(ABC):
    def __init__(self, text, url):
        self.url = url
        self.text = text

    def __str__(self):
        return self.url


class BlackCard(SDBCard):
    def __init__(self, text, url, requiredWhiteCards):
        super().__init__(text, url)
        self.requiredWhiteCards = requiredWhiteCards


class WhiteCard(SDBCard):
    pass


class SDBExpansion:
    def __init__(self):
        self.white = []
        self.black = []


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
        noWhiteCards = True
        for expansion in expansions:
            if len(self.cards[expansion].white) > 1:
                noWhiteCards = False
        if noWhiteCards:
            raise ValueError("No white cards in any of the given expansions: " + ", ".join(expansions))

        if expansions == []:
            expansions = self.expansionNames

        expansion = random.choice(expansions)
        while len(self.cards[expansion].white) == 0:
            expansion = random.choice(expansions)

        return random.choice(self.cards[expansion].white)
    

    def randomBlack(self, expansions=[]):
        noBlackCards = True
        for expansion in expansions:
            if len(self.cards[expansion].black) > 1:
                noBlackCards = False
        if noBlackCards:
            raise ValueError("No black cards in any of the given expansions: " + ", ".join(expansions))

        if expansions == []:
            expansions = self.expansionNames

        expansion = random.choice(expansions)
        while len(self.cards[expansion].black) == 0:
            expansion = random.choice(expansions)

        return random.choice(self.cards[expansion].black)