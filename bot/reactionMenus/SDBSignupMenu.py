from bot import botState
from . import ReactionMenu, expiryFunctions
from discord import Message, Colour, Member, Role, Forbidden
from typing import Dict, TYPE_CHECKING
from .. import lib
from ..scheduling import TimedTask
from ..cfg import cfg
from ..game import sdbGame, sdbPlayer
from datetime import timedelta


async def ownerOnlyStartGame(menu, reactingUser=None):
    if reactingUser == menu.game.owner:
        await menu.endSignups()


async def ownerOnlyCancelGame(menu, reactingUser=None):
    if reactingUser == menu.game.owner:
        await menu.cancelSignups()


class SDBSignupMenu(ReactionMenu.ReactionMenu):

    def __init__(self, msg : Message, game : sdbGame.SDBGame, timeToJoin : timedelta):

        self.game = game
        options = {cfg.defaultAcceptEmoji: ReactionMenu.NonSaveableReactionMenuOption("Join game", cfg.defaultAcceptEmoji, addFunc=self.userJoinGame, removeFunc=self.userLeaveGame),
                    cfg.defaultSubmitEmoji: ReactionMenu.NonSaveableReactionMenuOption("Force start game", cfg.defaultSubmitEmoji, addFunc=ownerOnlyStartGame, addArgs=self),
                    cfg.defaultCancelEmoji: ReactionMenu.NonSaveableReactionMenuOption("Cancel game", cfg.defaultCancelEmoji, addFunc=ownerOnlyCancelGame, addArgs=self)}
        timeout = TimedTask.TimedTask(expiryDelta=timeToJoin, expiryFunction=self.endSignups)
        botState.reactionMenusTTDB.scheduleTask(timeout)
        
        super().__init__(msg, options = options,
                    titleTxt = game.owner.display_name + " is playing Super Deck Breaker!",
                    desc = "Deck: " + game.deck.name +
                        "\nExpansions: " + ", ".join(game.expansionNames) +
                        "\n\nGame beginning in " + lib.timeUtil.td_format_noYM(timeToJoin) + "!",
                        timeout = timeout)


    async def userJoinGame(self, reactingUser=None):
        sendChannel = None

        if reactingUser.dm_channel is None:
            await reactingUser.create_dm()
        sendChannel = reactingUser.dm_channel
        
        try:
            await sendChannel.send("✅ You joined " + self.game.owner.name + "'s game!")
        except Forbidden:
            await self.msg.channel.send(":x: " + reactingUser.mention + " failed to join - I can't DM you! Please enable DMs from users who are not friends.")
            try:
                await self.msg.remove_reaction(cfg.defaultAcceptEmoji.sendable, reactingUser)
            except Forbidden:
                pass

        
    async def userLeaveGame(self, reactingUser=None):
        sendChannel = None

        if reactingUser.dm_channel is None:
            await reactingUser.create_dm()
        sendChannel = reactingUser.dm_channel
        
        try:
            await sendChannel.send("✅ You left " + self.game.owner.name + "'s game.")
        except Forbidden:
            pass

    
    async def endSignups(self):
        self.msg = await self.msg.channel.fetch_message(self.msg.id)
        reaction = [reaction for reaction in self.msg.reactions if lib.emojis.BasedEmoji.fromReaction(reaction.emoji) == cfg.defaultAcceptEmoji]
        if not reaction or reaction[0].count < 3:
            await self.msg.channel.send(":x: " + self.game.owner.mention + " Game cancelled: Not enough players joined the game.")
            await expiryFunctions.deleteReactionMenu(self.msg.id)
        else:
            reaction = reaction[0]
            self.game.players = []
            async for user in reaction.users():
                if user != self.msg.guild.me:
                    self.game.players.append(sdbPlayer.SDBPlayer(user, self.game))
            await expiryFunctions.deleteReactionMenu(self.msg.id)
            await self.game.startGame()


    async def cancelSignups(self):
        await self.msg.channel.send("The game was cancelled by the host.")
        await expiryFunctions.markExpiredMenu(self.msg.id)