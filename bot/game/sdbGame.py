from urllib import request
import json
from .. import botState
from typing import Dict, Union
from ..reactionMenus import expiryFunctions
from ..baseClasses.enum import Enum

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
        self.expansions = {}
        for expansionName in expansionNames:
            self.expansions[expansionName] = deckMeta["expansions"][expansionName]


async def startGameFromExpansionMenu(gameCfg : Dict[str, Union[str, int]]):
    menu = botState.reactionMenusDB[gameCfg["menuID"]]
    callingBGuild = botState.guildsDB.getGuild(menu.msg.guild.id)

    expansionNames = [option.name for option in menu.selectedOptions if menu.selectedOptions[option]]

    del callingBGuild.runningGames[menu.msg.channel]
    playChannel = menu.msg.channel

    await expiryFunctions.deleteReactionMenu(menu.msg.id)
    await callingBGuild.startGame(menu.targetMember, playChannel, gameCfg["deckName"], expansionNames)