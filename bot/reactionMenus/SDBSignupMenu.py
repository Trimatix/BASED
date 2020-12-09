from bot import botState
from . import ReactionMenu, expiryFunctions
from discord import Message, Colour, Member, Role
from typing import Dict, TYPE_CHECKING
from .. import lib
from ..scheduling import TimedTask
from ..cfg import cfg
from ..game import sdbGame
from datetime import timedelta

class SDBSignupMenu(ReactionMenu.ReactionMenu):

    def __init__(self, msg : Message, game : sdbGame.SDBGame, timeToJoin : timedelta):

        options = {cfg.defaultAcceptEmoji: ReactionMenu.DummyReactionMenuOption("Join game", cfg.defaultAcceptEmoji)}
        timeout = TimedTask.TimedTask(expiryDelta=timeToJoin, expiryFunction=expiryFunctions.deleteReactionMenu, expiryFunctionArgs=msg.id)
        botState.reactionMenusTTDB.scheduleTask(timeout)
        
        super().__init__(msg, options = options,
                    titleTxt = game.owner.display_name + " is playing Super Deck Breaker!",
                    desc = "Deck: " + game.deckName +
                        "\nExpansions: " + ", ".join(game.expansionNames) +
                        "\n\nGame beginning in " + lib.timeUtil.td_format_noYM(timeToJoin) + "!",
                        timeout = timeout)