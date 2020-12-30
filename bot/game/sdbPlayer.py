from .sdbDeck import SDBCard, WhiteCard
from .. import lib


class SDBCardSlot:
    def __init__(self, currentCard, message):
        self.currentCard = currentCard
        self.seleted = False
        self.message = message

    
    async def setCard(self, newCard):
        self.currentCard = newCard
        await self.message.edit(embed=lib.discordUtil.makeEmbed(img=newCard.url))

    
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


    async def submitCards(self):
        if len(self.selectedSlots) != self.game.currentBlackCard.requiredWhiteCards:
            raise ValueError("Player currently has " + str(len(self.selectedSlots)) + " card slots selected, but " + str(self.game.currentBlackCard.requiredWhiteCards) + " are required by the black card: " + str(self.game.currentBlackCard.url))
        self.submittedCards = []
        for slot in self.selectedSlots:
            self.submittedCards.append(slot.currentCard)
            await slot.setCard(SDBCard.SUBMITTED_CARD)

        self.selectedSlots = []
