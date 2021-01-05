from bot import botState
from . import ReactionMenu, expiryFunctions
from discord import Message, Colour, Member, Role, Forbidden
from typing import Dict, TYPE_CHECKING
from .. import lib
from ..scheduling import TimedTask
from ..cfg import cfg
from ..game import sdbGame, sdbPlayer
from datetime import timedelta


class SDBCardPlayMenu(ReactionMenu.ReactionMenu):
    def __init__(self, msg: Message, player: sdbPlayer.SDBPlayer):
        self.player = player
        self.menuEmbed = lib.discordUtil.makeEmbed(titleTxt="Play your cards")
        self.menuEmbed.add_field(name="Currently selected:", value="No cards selected​", inline=False)
        self.menuEmbed.add_field(name="White cards required this round:", value="Waiting for game to start...", inline=False)
        super().__init__(msg, options={cfg.defaultSubmitEmoji: ReactionMenu.NonSaveableReactionMenuOption("Submit cards", cfg.defaultSubmitEmoji, addFunc=self.player.submitCards)}, targetMember=player.dcUser)


    def getMenuEmbed(self):
        return self.menuEmbed


    async def updateEmbed(self, updateRequiredWhiteCards=False):
        newSelectedStr = "\n".join(str(slotNum + 1) + ". " + self.player.selectedSlots[slotNum].currentCard.text for slotNum in range(len(self.player.selectedSlots)) if not self.player.selectedSlots[slotNum].isEmpty)
        newSelectedStr = newSelectedStr if newSelectedStr else "No cards selected​"
        field = self.menuEmbed.fields[0]
        self.menuEmbed.set_field_at(0, name=field.name, value=newSelectedStr, inline=False)

        if updateRequiredWhiteCards:
            field = self.menuEmbed.fields[1]
            self.menuEmbed.set_field_at(1, name=field.name, value=str(self.player.game.currentBlackCard.currentCard.requiredWhiteCards), inline=False)

        await self.updateMessage(noRefreshOptions=True)


    async def addCardNumErr(self):
        self.menuEmbed.add_field(name="Incorrect number of cards selected", value="The current black card doesn't take this many white cards!", inline=False)
        await self.updateMessage(noRefreshOptions=True)
    
    async def remCardNumErr(self):
        self.menuEmbed.remove_field(-1)
        await self.updateMessage(noRefreshOptions=True)
