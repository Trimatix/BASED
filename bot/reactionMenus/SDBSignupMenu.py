from bot import botState
from . import ReactionMenu, expiryFunctions
from discord import Message, Colour, Member, Role, Forbidden, HTTPException, NotFound
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
        options = {cfg.defaultEmojis.accept: ReactionMenu.NonSaveableReactionMenuOption("Join game", cfg.defaultEmojis.accept, addFunc=self.userJoinGame, removeFunc=self.userLeaveGame),
                    cfg.defaultEmojis.submit: ReactionMenu.NonSaveableReactionMenuOption("Force start game", cfg.defaultEmojis.submit, addFunc=ownerOnlyStartGame, addArgs=self),
                    cfg.defaultEmojis.cancel: ReactionMenu.NonSaveableReactionMenuOption("Cancel game", cfg.defaultEmojis.cancel, addFunc=ownerOnlyCancelGame, addArgs=self)}
        timeout = TimedTask.TimedTask(expiryDelta=timeToJoin, expiryFunction=self.endSignups)
        botState.reactionMenusTTDB.scheduleTask(timeout)
        self.numSignups = 0
        
        super().__init__(msg, options = options,
                    titleTxt = game.owner.display_name + " is playing Super Deck Breaker!",
                    desc = "Deck: " + game.deck.name +
                        "\nMax players: " + str(game.maxPlayers) +
                        "\nRounds: " + (("Best of " + str(game.rounds)) if game.rounds != -1 else "Free play") +
                        "\nExpansions: " + ", ".join(game.expansionNames) +
                        "\n\nGame beginning in " + lib.timeUtil.td_format_noYM(timeToJoin) + "!",
                        timeout = timeout)


    async def userJoinGame(self, reactingUser=None):
        sendChannel = None

        if reactingUser.dm_channel is None:
            await reactingUser.create_dm()
        sendChannel = reactingUser.dm_channel
        
        try:
            if self.numSignups == self.game.maxPlayers:
                await sendChannel.send("This game is full!")
                try:
                    await self.msg.remove_reaction(cfg.defaultEmojis.accept.sendable, reactingUser)
                except (Forbidden, NotFound, HTTPException):
                    pass
            else:
                self.numSignups += 1
                await sendChannel.send("✅ You joined " + self.game.owner.name + "'s game!")
        except Forbidden:
            await self.msg.channel.send(":x: " + reactingUser.mention + " failed to join - I can't DM you! Please enable DMs from users who are not friends.")
            try:
                await self.msg.remove_reaction(cfg.defaultEmojis.accept.sendable, reactingUser)
            except (Forbidden, NotFound, HTTPException):
                pass

        
    async def userLeaveGame(self, reactingUser=None):
        self.numSignups -= 1
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
        reaction = [reaction for reaction in self.msg.reactions if lib.emojis.BasedEmoji.fromReaction(reaction.emoji, rejectInvalid=False) == cfg.defaultEmojis.accept]
        if not reaction or self.numSignups < cfg.minPlayerCount:
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