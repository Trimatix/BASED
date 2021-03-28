from .sdbDeck import SDBCard, WhiteCard
from .. import lib, botState
from ..reactionMenus import SDBDMConfigMenu
from ..cfg import cfg


class SDBCardSlot:
    def __init__(self, currentCard, message, player):
        self.currentCard = currentCard
        self.message = message
        self.isEmpty = currentCard is None
        self.player = player

    
    async def setCard(self, newCard, updateMessage = True):
        self.currentCard = newCard
        if self.player is not None:
            newCard.claim(self.player)
        if updateMessage:
            await self.message.edit(embed=lib.discordUtil.makeEmbed(img=newCard.url, desc=newCard.url if cfg.debugCards else ""))
        self.isEmpty = False
    

    async def removeCard(self, emptyCard, updateMessage = True):
        if self.player is not None:
            self.currentCard.revoke()
        if updateMessage:
            await self.message.edit(embed=lib.discordUtil.makeEmbed(img=emptyCard.url, desc=emptyCard.url if cfg.debugCards else ""))
        self.isEmpty = True


class SDBPlayer:
    def __init__(self, dcUser, game):
        self.dcUser = dcUser
        self.hand = []
        self.game = game
        self.hasSubmitted = False
        self.submittedCards = []
        self.selectedSlots = []
        self.points = 0
        self.playMenu = None
        self.hasCardNumErr = False
        self.isChooser = False
        self.chooserSubmitError = None
        self.alreadySubmittedError = None
        self.configMenu = None
        self.hasRedealt = False
        self.selectorMenus = []
        self.cardsSubmittedMsg = None


    async def submitCards(self):
        if self.isChooser:
            if self.chooserSubmitError is None:
                self.chooserSubmitError = await self.dcUser.send("You can't submit cards yet as you are the card chooser!")
        elif self.hasSubmitted or not self.game.waitingForSubmissions:
            if self.alreadySubmittedError is None:
                self.alreadySubmittedError = await self.dcUser.send("You've already submitted for this round!")
        elif len(self.selectedSlots) != self.game.currentBlackCard.currentCard.requiredWhiteCards:
            await self.removeErrs(noCardNumErr=True)

            # raise ValueError("Player currently has " + str(len(self.selectedSlots)) + " card slots selected, but " + str(self.game.currentBlackCard.currentCard.requiredWhiteCards) + " are required by the black card: " + str(self.game.currentBlackCard.url))
            if not self.hasCardNumErr:
                await self.playMenu.addCardNumErr()
                self.hasCardNumErr = True
        else:                
            self.submittedCards = []
            for slot in self.selectedSlots:
                self.submittedCards.append(slot.currentCard)
                await slot.removeCard(self.game.deck.emptyWhite)

            self.hasSubmitted = True
            await self.removeErrs()
            self.cardsSubmittedMsg = await self.dcUser.send("✅ Cards submitted!")
            await self.game.submissionReceived(self)


    def hasCard(self, card):
        for c in self.hand:
            if c == card:
                return True
        return False


    async def updatePlayMenu(self):
        await self.playMenu.updateEmbed(updateRequiredWhiteCards=(self.game.currentBlackCard is not None) and (not self.game.currentBlackCard.isEmpty))


    def hasConfigMenu(self):
        return self.configMenu is not None


    async def closeConfigMenu(self):
        if not self.hasConfigMenu():
            raise RuntimeError("Attempted to closeConfigMenu when player has no config menu: " + self.dcUser.name + "#" + str(self.dcUser.id) + " in game " + self.game.guild.name + "->" + self.game.channel.name)
        await self.configMenu.delete()
    

    async def makeConfigMenu(self, owningMsg=None):
        if not self.dcUser == self.game.owner:
            raise RuntimeError("Attempted to makeConfigMenu on a player who is not the game owner: " + self.dcUser.name + "#" + str(self.dcUser.id) + " in game " + self.game.guild.name + "->" + self.game.channel.name)
        
        if self.hasConfigMenu():
            await self.closeConfigMenu()

        cfgMenuMsg = await lib.discordUtil.sendDM("​", self.dcUser, owningMsg, reactOnDM=owningMsg is not None)
        if cfgMenuMsg is not None:
            self.configMenu = SDBDMConfigMenu.SDBDMConfigMenu(cfgMenuMsg, self.game)
            botState.reactionMenusDB[cfgMenuMsg.id] = self.configMenu
            await self.configMenu.updateMessage()

    
    async def removeErrs(self, noCardNumErr=False):
        if self.cardsSubmittedMsg is not None:
            await self.cardsSubmittedMsg.delete()
            self.cardsSubmittedMsg = None
        if self.chooserSubmitError is not None:
            await self.chooserSubmitError.delete()
            self.chooserSubmitError = None
        if self.alreadySubmittedError is not None:
            await self.alreadySubmittedError.delete()
            self.alreadySubmittedError = None
        if not noCardNumErr and self.hasCardNumErr:
            await self.playMenu.remCardNumErr()


    def __hash__(self) -> int:
        return hash(repr(self))
