import json
# from urllib import request
import random
from abc import ABC, abstractmethod
from typing import List, Dict
from discord import Message
from datetime import datetime
import os

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from .. import lib
from .. import botState
from ..cfg import cfg
from ..cardRenderer import make_cards


# use creds to create a client to interact with the Google Drive API
scope = ['https://spreadsheets.google.com/feeds']
creds = ServiceAccountCredentials.from_json_keyfile_name(cfg.paths.googleAPICred, scope)
gspread_client = gspread.authorize(creds)

def collect_cards(sheetLink):
    global gspread_client

    worksheet = gspread_client.open_by_url(sheetLink)
    expansions = {}

    for expansion in worksheet.worksheets():
        expansions[expansion.title] = {"white": [card for card in expansion.col_values(1) if card],
                                        "black": [card for card in expansion.col_values(2) if card]}

    return {"expansions": expansions, "title": worksheet.title}


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
    def __init__(self, metaPath: str):
        # deckMeta = json.load(request.urlopen(metaUrl))
        deckMeta = lib.jsonHandler.readJSON(metaPath)

        if "expansions" not in deckMeta or deckMeta["expansions"] == {}:
            raise RuntimeError("Attempted to create an empty SDBDeck")

        self.expansionNames: List[str] = list(deckMeta["expansions"].keys())
        self.cards: Dict[str, SDBExpansion] = {expansion : SDBExpansion() for expansion in self.expansionNames}
        self.name: str = deckMeta["deck_name"]
        hasWhiteCards: bool = False
        hasBlackCards: bool = False

        for expansion in self.expansionNames:
            if "white" in deckMeta["expansions"][expansion]:
                for cardData in deckMeta["expansions"][expansion]["white"]:
                    self.cards[expansion].white.append(WhiteCard(cardData["text"], cardData["url"], self.cards[expansion]))
            if "black" in deckMeta["expansions"][expansion]:
                for cardData in deckMeta["expansions"][expansion]["black"]:
                    self.cards[expansion].black.append(BlackCard(cardData["text"], cardData["url"], cardData["requiredWhiteCards"], self.cards[expansion]))

            if not hasWhiteCards:
                hasWhiteCards = len(self.cards[expansion].white) != 0
            if not hasBlackCards:
                hasBlackCards = len(self.cards[expansion].black) != 0

        if not hasWhiteCards:
            raise RuntimeError("Attempted to create a deck with no white cards")
        elif not hasBlackCards:
            raise RuntimeError("Attempted to create a deck with no black cards")

        self.emptyBlack: BlackCard = BlackCard("EMPTY", deckMeta["black_back"] if "black_back" in deckMeta else cfg.emptyBlackCard, 0, list(self.cards.values())[0])
        self.emptyWhite: WhiteCard = WhiteCard("EMPTY", deckMeta["white_back"] if "white_back" in deckMeta else cfg.emptyWhiteCard, list(self.cards.values())[0])


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


async def updateDeck(callingMsg: Message, bGuild, deckName: str):
    loadingMsg = await callingMsg.reply("Reading spreadsheet... " + cfg.defaultEmojis.loading.sendable)

    try:
        newCardData = collect_cards(bGuild.decks[deckName]["spreadsheet_url"])
        await loadingMsg.edit(content="Reading spreadsheet... " + cfg.defaultEmojis.submit.sendable)
    except gspread.SpreadsheetNotFound:
        await callingMsg.reply(":x: Unrecognised spreadsheet! Please make sure the file exists and is public.")
        bGuild.decks[deckName]["updating"] = False
        return
    else:
        lowerExpansions = [expansion.lower() for expansion in newCardData["expansions"]]
        for expansion in lowerExpansions:
            if lowerExpansions.count(expansion) > 1:
                await callingMsg.reply(":x: Deck update failed - duplicate expansion pack name found: " + expansion)
                bGuild.decks[deckName]["updating"] = False
                return
        
        unnamedFound = False
        emptyExpansions = []
        for expansion in newCardData["expansions"]:
            if expansion == "":
                unnamedFound = True
            if len(newCardData["expansions"][expansion]["white"]) == 0 and len(newCardData["expansions"][expansion]["black"]) == 0:
                emptyExpansions.append(expansion)

        errs = ""
        
        if unnamedFound:
            errs += "\nUnnamed expansion pack detected - skipping this expansion."
            del newCardData["expansions"][""]

        if len(emptyExpansions) != 0:
            errs += "\nEmpty expansion packs detected - skipping these expansions: " + ", ".join(expansion for expansion in emptyExpansions)
            for expansion in emptyExpansions:
                del newCardData["expansions"][expansion]
        
        if errs != "":
            await callingMsg.channel.send(errs)

        whiteCounts = {expansion: len(newCardData["expansions"][expansion]["white"]) for expansion in newCardData["expansions"]}
        blackCounts = {expansion: len(newCardData["expansions"][expansion]["black"]) for expansion in newCardData["expansions"]}

        totalWhite = sum(whiteCounts.values())
        totalBlack = sum(blackCounts.values())
        
        if int(totalWhite / cfg.cardsPerHand) < 2:
            await callingMsg.reply("Deck update failed.\nDecks must have at least " + str(2 * cfg.cardsPerHand) + " white cards.")
            bGuild.decks[deckName]["updating"] = False
            return
        if totalBlack == 0:
            await callingMsg.reply("Deck update failed.\nDecks must have at least 1 black card.")
            bGuild.decks[deckName]["updating"] = False
            return

        oldCardData = lib.jsonHandler.readJSON(bGuild.decks[deckName]["meta_path"])
        deckID = os.path.splitext(os.path.split(bGuild.decks[deckName]["meta_path"])[1])[0]

        cardStorageChannel = None if cfg.cardStorageMethod == "local" else botState.client.get_guild(cfg.cardsDCChannel["guild_id"]).get_channel(cfg.cardsDCChannel["channel_id"])

        loadingMsg = await callingMsg.channel.send("Updating deck... " + cfg.defaultEmojis.loading.sendable)
        results = await make_cards.update_deck(cfg.paths.decksFolder, oldCardData, newCardData, deckID, cfg.paths.cardFont, callingMsg.guild.id, emptyExpansions, cfg.cardStorageMethod, cardStorageChannel, callingMsg, contentFontSize=cfg.cardContentFontSize, titleFontSize=cfg.cardTitleFontSize)
        oldCardData, changeLog = results[0], results[1]

        await loadingMsg.edit(content="Updating deck... " + cfg.defaultEmojis.submit.sendable)
        
        lib.jsonHandler.writeJSON(bGuild.decks[deckName]["meta_path"], oldCardData)
        now = datetime.utcnow()
        bGuild.decks[deckName]["last_update"] = now.timestamp()
        bGuild.decks[deckName]["expansions"] = {expansion: (whiteCounts[expansion], blackCounts[expansion]) for expansion in whiteCounts}
        bGuild.decks[deckName]["white_count"] = totalWhite
        bGuild.decks[deckName]["black_count"] = totalBlack

        bGuild.decks[deckName]["updating"] = False
        if changeLog == "":
            await callingMsg.reply("Update complete, no changes found!")
        else:
            await callingMsg.reply("Update complete!\n" + changeLog)
