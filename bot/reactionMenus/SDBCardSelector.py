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


    async def updateMessage(self, noRefreshOptions=False, noUpdateEmbed=True):
        return await super().updateMessage(noRefreshOptions=noRefreshOptions, noUpdateEmbed=noUpdateEmbed)