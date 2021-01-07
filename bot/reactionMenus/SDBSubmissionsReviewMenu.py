from . import PagedReactionMenu, ReactionMenu
from discord import Embed, Member, Role
from ..users import basedUser
from ..cfg import cfg
from ..game import sdbPlayer


class SDBWinningSubmissionOption(ReactionMenu.DummyReactionMenuOption):
    def __init__(self, player: sdbPlayer.SDBPlayer, name="Select winning player", emoji=cfg.defaultAcceptEmoji):
        super().__init__(name, emoji)
        self.player = player


class InlineSDBSubmissionsReviewMenu(PagedReactionMenu.InlinePagedReactionMenu):
    def __init__(self, msg, game, timeoutSeconds, multiCard, targetMember : Member, chooserPlayer):
        pages = {}
        returnTriggers = []
        for player in game.players:
            if not player.isChooser:
                for cardNum in range(len(player.submittedCards)):
                    currentEmbed = Embed()
                    currentEmbed.title = player.dcUser.display_name
                    currentEmbed.set_image(url=player.submittedCards[cardNum].url)
                    if multiCard:
                        currentEmbed.set_footer(text="Card " + str(cardNum+1))
                    
                    newOption = SDBWinningSubmissionOption(player)
                    pages[currentEmbed] = {cfg.defaultAcceptEmoji: newOption}
                    returnTriggers.append(newOption)
        
        self.chooserPlayer = chooserPlayer

        super().__init__(msg, timeoutSeconds, pages=pages, targetMember=targetMember, noCancel=True, returnTriggers=returnTriggers, anon=True)


    async def reactionClosesMenu(self, reactPL):
        return not self.chooserPlayer.isChooser or await super().reactionClosesMenu(reactPL)


    def reactionValid(self, reactPL):
        return not self.chooserPlayer.isChooser or super().reactionValid(reactPL)