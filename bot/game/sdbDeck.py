import json
from urllib import request
import random
from abc import ABC

from ..cfg import cfg


class SDBCard(ABC):
    def __init__(self, url):
        self.url = url
        
    def isEmpty(self):
        return self.url == cfg.emptyCard


    def __str__(self):
        return self.url


class BlackCard(SDBCard):
    EMPTY_CARD = None

    def __init__(self, url, requiredWhiteCards):
        super().__init__(url)
        self.requiredWhiteCards = requiredWhiteCards


BlackCard.EMPTY_CARD = SDBCard(cfg.emptyBlackCard)


class WhiteCard(SDBCard):
    EMPTY_CARD = None
    SUBMITTED_CARD = None


WhiteCard.EMPTY_CARD = SDBCard(cfg.emptyWhiteCard)
WhiteCard.SUBMITTED_CARD = SDBCard(cfg.submittedWhiteCard)



class SDBExpansion:
    def __init__(self):
        self.white = []
        self.black = []


class SDBDeck:
    def __init__(self, metaUrl):
        deckMeta = json.load(request.urlopen(metaUrl))
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
                    self.cards[expansion].white.append(WhiteCard(cardData["url"]))
            if "black" in deckMeta["expansions"][expansion]:
                for cardData in deckMeta["expansions"][expansion]["black"]:
                    self.cards[expansion].black.append(BlackCard(cardData["url"], cardData["requiredWhiteCards"]))

            if not hasWhiteCards:
                hasWhiteCards = len(self.cards[expansion].white) != 0
            if not hasBlackCards:
                hasBlackCards = len(self.cards[expansion].black) != 0

        if not hasWhiteCards:
            raise RuntimeError("Attempted to create a deck with no white cards")
        elif not hasBlackCards:
            raise RuntimeError("Attempted to create a deck with no black cards")


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