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
        self.menuEmbed.add_field(name="Currently selected:", value="No cards selected​")
        super().__init__(msg, options={cfg.defaultSubmitEmoji: ReactionMenu.NonSaveableReactionMenuOption("Submit cards", cfg.defaultSubmitEmoji, addFunc=self.player.submitCards)}, targetMember=player.dcUser)


    def getMenuEmbed(self):
        return self.menuEmbed


    async def updateSelectionsField(self):
        newSelectedStr = "\n".join(str(slotNum) + ". " + self.player.selectedSlots[slotNum].currentCard.text for slotNum in range(len(self.player.selectedSlots))) if self.player.selectedSlots else "No cards selected​"
        # str(len(self.player.selectedSlots))
        for fieldIndex in range(len(self.menuEmbed.fields)):
            field = self.menuEmbed.fields[fieldIndex]
            if field.name == "Currently selected:":
                self.menuEmbed.set_field_at(fieldIndex, name=field.name, value=newSelectedStr)
            break

        await self.updateMessage(noRefreshOptions=True)