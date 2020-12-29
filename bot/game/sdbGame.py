from urllib import request
import json
from .. import botState
from typing import Dict, Union
from ..reactionMenus import expiryFunctions
from ..baseClasses.enum import Enum
from ..cfg import cfg
import random

class GamePhase(Enum):
    setup = -1
    playRound = 0
    postRound = 1
    gameOver = 2


class SDBGame:
    def __init__(self, owner, meta_url, expansionNames, gamePhase=GamePhase.setup):
        self.owner = owner
        self.meta_url = meta_url
        deckMeta = json.load(request.urlopen(meta_url))
        self.expansionNames = expansionNames
        self.deckName = deckMeta["deck_name"]
        self.gamePhase = gamePhase
        self.players = []
        self.expansions = {}
        for expansionName in expansionNames:
            self.expansions[expansionName] = deckMeta["expansions"][expansionName]


    async def dealCards(self):
        for player in self.players:
            for missingCardNum in range(cfg.cardsPerHand - len(player.hand)):
                player.hand.append(random.choice(self.expansions[random.choice(self.expansionNames)]))


    async def advanceGame(self):
        if self.gamePhase == GamePhase.setup:
            await self.dealCards()
            await self.doGameIntro()
        elif self.gamePhase == GamePhase.playRound:
            await self.pickWinningCards()
        elif self.gamePhase == GamePhase.postRound:
            await self.dealCards()
        elif self.gamePhase == GamePhase.gameOver:
            await self.showLeaderboard()


async def startGameFromExpansionMenu(gameCfg : Dict[str, Union[str, int]]):
    menu = botState.reactionMenusDB[gameCfg["menuID"]]
    callingBGuild = botState.guildsDB.getGuild(menu.msg.guild.id)

    expansionNames = [option.name for option in menu.selectedOptions if menu.selectedOptions[option]]

    del callingBGuild.runningGames[menu.msg.channel]
    playChannel = menu.msg.channel

    await expiryFunctions.deleteReactionMenu(menu.msg.id)
    await callingBGuild.startGameSignups(menu.targetMember, playChannel, gameCfg["deckName"], expansionNames)