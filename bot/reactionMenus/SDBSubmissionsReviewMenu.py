from bot import botState
from . import PagedReactionMenu, ReactionMenu
from discord import Embed, Message, Embed, File
from ..cfg import cfg
from ..game import sdbPlayer, sdbGame
from typing import Dict, List, TYPE_CHECKING
from .. import lib
from concurrent import futures
import psutil
from PIL import Image
from ..cardRenderer.lib import url_to_local_path, CARD_SIZE, local_file_url, IMG_FORMAT
import io
import os
import shutil


class SDBWinningSubmissionOption(ReactionMenu.DummyReactionMenuOption):
    def __init__(self, player: "sdbPlayer.SDBPlayer", name="Select winning player", emoji=cfg.defaultEmojis.accept):
        super().__init__(name, emoji)
        self.player = player


class InlineSDBSubmissionsReviewMenu(PagedReactionMenu.InlinePagedReactionMenu):
    def __init__(self, msg: Message, pages: Dict[Embed, Dict[lib.emojis.BasedEmoji, SDBWinningSubmissionOption]], returnTriggers: List[SDBWinningSubmissionOption], timeoutSeconds: int, chooserPlayer: "sdbPlayer.SDBPlayer"):        
        self.chooserPlayer = chooserPlayer

        super().__init__(msg, timeoutSeconds, pages=pages, targetMember=chooserPlayer.dcUser, noCancel=True, returnTriggers=returnTriggers, anon=True)


    async def reactionClosesMenu(self, reactPL):
        return not self.chooserPlayer.isChooser or await super().reactionClosesMenu(reactPL)


    def reactionValid(self, reactPL):
        return not self.chooserPlayer.isChooser or super().reactionValid(reactPL)


class InlineSequentialSubmissionsReviewMenu(InlineSDBSubmissionsReviewMenu):
    def __init__(self, msg: Message, game: "sdbGame.SDBGame", timeoutSeconds: int):
        chooserPlayer = game.getChooser()
        multiCard = game.currentBlackCard.currentCard.requiredWhiteCards > 1
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
                    pages[currentEmbed] = {cfg.defaultEmojis.accept: newOption}
                    returnTriggers.append(newOption)
        
        super().__init__(msg, pages, returnTriggers, timeoutSeconds, chooserPlayer)


class InlineMergedSubmissionsReviewMenu(InlineSDBSubmissionsReviewMenu):
    def __init__(self, msg: Message, submissions: Dict["sdbPlayer.SDBPlayer", str], timeoutSeconds: int, chooserPlayer: "sdbPlayer.SDBPlayer"):
        pages = {}
        returnTriggers = []
        for player in submissions:
            currentEmbed = Embed()
            currentEmbed.title = player.dcUser.display_name
            currentEmbed.set_image(url=submissions[player])
            
            newOption = SDBWinningSubmissionOption(player)
            pages[currentEmbed] = {cfg.defaultEmojis.accept: newOption}
            returnTriggers.append(newOption)

        super().__init__(msg, pages, returnTriggers, timeoutSeconds, chooserPlayer)


def mergeImageTable(images: List[Image.Image], lineLength: int) -> Image.Image:
    tableWidth = min(len(images), lineLength)
    tableHeight = int((len(images) - 1) / lineLength) + 1
    newIm = Image.new('RGB', (CARD_SIZE[0] * tableWidth, CARD_SIZE[1] * tableHeight))

    for imNum in range(len(images)):
        col = imNum % tableWidth
        row = int(imNum / tableWidth)
        newIm.paste(images[imNum], (CARD_SIZE[0] * col, CARD_SIZE[1] * row))

    return newIm


def loadImages(imagePaths: List[str]) -> List[Image.Image]:
    return [Image.open(path) for path in imagePaths]


async def buildMergedSubmissionsMenuImages(game: "sdbGame.SDBGame") -> Dict[Embed, Dict[lib.emojis.BasedEmoji, SDBWinningSubmissionOption]]:
    mergedSubmissionImages = {}

    async def mergePlayerSubmissions(player: "sdbPlayer.SDBPlayer"):
        print("merge submissions for player: " + player.dcUser.display_name)
        cardImages = []
        useLocal = cfg.cardStorageMethod == "local"
        if useLocal:
            try:
                cardImages = loadImages(url_to_local_path(card.url) for card in player.submitCards)
            except FileNotFoundError:
                useLocal = False
        
        if not useLocal:
            for card in player.submittedCards:
                async with botState.httpClient.get(card.url) as resp:
                    if resp.status == 200:
                        cardImages.append(Image.open(io.BytesIO(await resp.read())))

        mergedSubmissionImages[player] = mergeImageTable(cardImages, cfg.mergedSubmissionsMenu_lineLength)
        for img in cardImages:
            img.close()

    for player in game.players:
        if not player.isChooser:
            await mergePlayerSubmissions(player)
    # with futures.ThreadPoolExecutor(len(psutil.Process().cpu_affinity())) as executor:
    #     executor.map(
    #         lambda player: mergePlayerSubmissions(player),
    #         [player for player in game.players if not player.isChooser]
    #     )
    
    uploadedSubmissionsImages = {}
    storageChannel = botState.client.get_guild(cfg.cardsDCChannel["guild_id"]).get_channel(cfg.cardsDCChannel["channel_id"])

    if cfg.cardStorageMethod == "discord":
        for player in mergedSubmissionImages:
            submissionBytes = io.BytesIO()
            mergedSubmissionImages[player].save(submissionBytes, format="JPEG")
            submissionBytes.seek(0)
            dcFile = File(submissionBytes, filename="merged-submissions.JPEG")
            newMsg = await storageChannel.send(file=dcFile)
            uploadedSubmissionsImages[player] = newMsg.attachments[0].url
    
    elif cfg.cardStorageMethod == "local":
        roundCardsDir = cfg.paths.cardsTemp + os.sep + str(game.channel.id) + os.sep + str(game.currentRound)
        if os.path.isdir(roundCardsDir):
            shutil.rmtree(roundCardsDir)
        os.makedirs(roundCardsDir)

        for player in mergedSubmissionImages:
            cardHash = player.dcUser.id
            cardPath = roundCardsDir + os.sep + str(cardHash) + "." + IMG_FORMAT
            mergedSubmissionImages[player].save(cardPath)
            uploadedSubmissionsImages[player] = local_file_url(cardPath)
    
    else:
        raise ValueError("Unsupported cardStorageMethod: " + str(cfg.cardStorageMethod))

    for img in mergedSubmissionImages.values():
        img.close()

    return uploadedSubmissionsImages

