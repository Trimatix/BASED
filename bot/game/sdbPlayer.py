from .sdbDeck import SDBCard, WhiteCard
from .. import lib


class SDBCardSlot:
    def __init__(self, currentCard, message, player):
        self.currentCard = currentCard
        self.message = message
        self.isEmpty = currentCard is None
        self.player = player

    
    async def setCard(self, newCard):
        self.currentCard = newCard
        if self.player is not None:
            newCard.claim(self.player)
        await self.message.edit(embed=lib.discordUtil.makeEmbed(img=newCard.url))
        self.isEmpty = False
    

    async def removeCard(self, emptyCard):
        if self.player is not None:
            self.currentCard.revoke()
        await self.setCard(emptyCard)
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


    async def submitCards(self):
        if self.isChooser:
            if self.chooserSubmitError is None:
                self.chooserSubmitError = await self.dcUser.send("You can't submit cards yet as you are the card chooser!")
        elif self.hasSubmitted:
                self.alreadySubmittedError = await self.dcUser.send("You've already submitted for this round!")
        elif len(self.selectedSlots) != self.game.currentBlackCard.currentCard.requiredWhiteCards:
            if self.chooserSubmitError is not None:
                await self.chooserSubmitError.delete()
                self.chooserSubmitError = None
            if self.alreadySubmittedError is not None:
                await self.alreadySubmittedError.delete()
                self.alreadySubmittedError = None

            # raise ValueError("Player currently has " + str(len(self.selectedSlots)) + " card slots selected, but " + str(self.game.currentBlackCard.currentCard.requiredWhiteCards) + " are required by the black card: " + str(self.game.currentBlackCard.url))
            if not self.hasCardNumErr:
                await self.playMenu.addCardNumErr()
                self.hasCardNumErr = True
        else:
            if self.chooserSubmitError is not None:
                await self.chooserSubmitError.delete()
                self.chooserSubmitError = None
            if self.alreadySubmittedError is not None:
                await self.alreadySubmittedError.delete()
                self.alreadySubmittedError = None

            if self.hasCardNumErr:
                await self.playMenu.remCardNumErr()
                
            self.submittedCards = []
            for slot in self.selectedSlots:
                self.submittedCards.append(slot.currentCard)
                await slot.removeCard(self.game.deck.emptyWhite)

            self.hasSubmitted = True


    def hasCard(self, card):
        for c in self.hand:
            if c == card:
                return True
        return False


    async def updatePlayMenu(self):
        await self.playMenu.updateEmbed(updateRequiredWhiteCards=(self.game.currentBlackCard is not None) and (not self.game.currentBlackCard.isEmpty))
