from bot import botState
from . import ReactionMenu, expiryFunctions
from discord import Message, Colour, Member, Role, Forbidden
from typing import Dict, TYPE_CHECKING
from .. import lib
from ..scheduling import TimedTask
from ..cfg import cfg
from ..game import sdbGame, sdbPlayer
from datetime import timedelta


class SDBCardSelector(ReactionMenu.ReactionMenu):
    def __init__(self, msg: Message, player: sdbPlayer.SDBPlayer, cardSlot: sdbPlayer.SDBCardSlot):
        super().__init__(msg, options={cfg.defaultAcceptEmoji: ReactionMenu.NonSaveableReactionMenuOption("Select card", cfg.defaultAcceptEmoji, addFunc=self.selectCard, removeFunc=self.deselectCard)}, targetMember=player.dcUser)
        self.player = player
        self.cardSlot = cardSlot


    async def selectCard(self):
        self.player.selectedSlots.append(self.cardSlot)
        await self.player.updatePlayMenu()

    
    async def deselectCard(self):
        self.player.selectedSlots.remove(self.cardSlot)
        await self.player.updatePlayMenu()


    async def delete(self):
        """⚠ WARNING: DO NOT SET THIS AS YOUR MENU'S TIMEDTASK EXPIRY FUNCTION. This method calls the menu's TimedTask expiry function.
        Forcibly delete the menu.
        If a timeout TimedTask was defined in this menu's constructor, this will be forcibly expired.
        If no TimedTask was given, the menu will default to calling deleteReactionMenu.
        """
        if self.timeout is None:
            if self.msg.id in botState.reactionMenusDB:
                del botState.reactionMenusDB[self.msg.id]
        else:
            await self.timeout.forceExpire()


    async def updateMessage(self, noRefreshOptions=False, noUpdateEmbed=True):
        return await super().updateMessage(noRefreshOptions=noRefreshOptions, noUpdateEmbed=noUpdateEmbed)