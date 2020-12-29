from bot import botState
from . import ReactionMenu, expiryFunctions
from discord import Message, Colour, Member, Role, Forbidden
from typing import Dict, TYPE_CHECKING
from .. import lib
from ..scheduling import TimedTask
from ..cfg import cfg
from ..game import sdbGame
from datetime import timedelta


async def userJoinGame(menuID, reactingUser=None):
    menu = botState.reactionMenusDB[menuID]
    sendChannel = None

    print(reactingUser.name + " joined " + menu.game.owner.name + "'s game")

    if reactingUser.dm_channel is None:
        await reactingUser.create_dm()
    sendChannel = reactingUser.dm_channel
    
    try:
        await sendChannel.send("✅ You joined " + menu.game.owner.name + "'s game!")
    except Forbidden:
        await menu.msg.channel.send(":x: " + reactingUser.mention + " failed to join - I can't DM you! Please enable DMs from users who are not friends.")
        try:
            await menu.msg.remove_reaction(cfg.defaultAcceptEmoji, reactingUser)
        except Forbidden:
            pass

    
async def userLeaveGame(menuID, reactingUser=None):
    menu = botState.reactionMenusDB[menuID]
    sendChannel = None

    if reactingUser.dm_channel is None:
        await reactingUser.create_dm()
    sendChannel = reactingUser.dm_channel
    
    try:
        await sendChannel.send("✅ You left " + menu.game.owner.name + "'s game.")
    except Forbidden:
        pass


class SDBSignupMenu(ReactionMenu.ReactionMenu):

    def __init__(self, msg : Message, game : sdbGame.SDBGame, timeToJoin : timedelta):

        self.game = game
        options = {cfg.defaultAcceptEmoji: ReactionMenu.NonSaveableReactionMenuOption("Join game", cfg.defaultAcceptEmoji, addFunc=userJoinGame, addArgs=msg.id, removeFunc=userLeaveGame, removeArgs=msg.id)}
        timeout = TimedTask.TimedTask(expiryDelta=timeToJoin, expiryFunction=expiryFunctions.deleteReactionMenu, expiryFunctionArgs=msg.id)
        botState.reactionMenusTTDB.scheduleTask(timeout)
        
        super().__init__(msg, options = options,
                    titleTxt = game.owner.display_name + " is playing Super Deck Breaker!",
                    desc = "Deck: " + game.deckName +
                        "\nExpansions: " + ", ".join(game.expansionNames) +
                        "\n\nGame beginning in " + lib.timeUtil.td_format_noYM(timeToJoin) + "!",
                        timeout = timeout)