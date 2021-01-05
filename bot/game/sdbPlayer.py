from .sdbDeck import SDBCard, WhiteCard
from .. import lib


class SDBCardSlot:
    def __init__(self, currentCard, message):
        self.currentCard = currentCard
        self.seleted = False
        self.message = message

    
    async def setCard(self, newCard):
        self.currentCard = newCard
        await self.message.edit(content=newCard.url, embed=lib.discordUtil.makeEmbed(img=newCard.url))

    
    def isEmpty(self):
        return self.currentCard in [WhiteCard.EMPTY_CARD, WhiteCard.SUBMITTED_CARD]


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


    async def submitCards(self):
        if len(self.selectedSlots) != self.game.currentBlackCard.currentCard.requiredWhiteCards:
            raise ValueError("Player currently has " + str(len(self.selectedSlots)) + " card slots selected, but " + str(self.game.currentBlackCard.currentCard.requiredWhiteCards) + " are required by the black card: " + str(self.game.currentBlackCard.url))
        self.submittedCards = []
        for slot in self.selectedSlots:
            self.submittedCards.append(slot.currentCard)
            await slot.setCard(WhiteCard.SUBMITTED_CARD)

        self.selectedSlots = []
        self.hasSubmitted = True

    async def updatePlayMenu(self):
        await self.playMenu.updateSelectionsField()