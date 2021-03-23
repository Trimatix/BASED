from discord import Embed, File, Message, Colour, Member, TextChannel
from .. import botState, lib
from typing import Dict, Union, List
from ..reactionMenus import expiryFunctions
from ..baseClasses.enum import Enum
from ..cfg import cfg
from . import sdbPlayer, sdbDeck
import asyncio
from ..reactionMenus.SDBSubmissionsReviewMenu import InlineSequentialSubmissionsReviewMenu
from ..reactionMenus.confirmationReactionMenu import InlineConfirmationMenu
from ..reactionMenus.SDBCardPlayMenu import SDBCardPlayMenu
from ..reactionMenus.SDBCardSelector import SDBCardSelector
from ..reactionMenus.pagedReactionMenu import InvalidClosingReaction
import random
import shutil
import os
from datetime import datetime
# from . import sdbGameConfig

from bot.reactionMenus import SDBSubmissionsReviewMenu
EMPTY_IMAGE = "https://i.imgur.com/sym17F7.png"


class DeckUpdateRegistry:
    def __init__(self, callingMsg: Message, bGuild):
        self.callingMsg = callingMsg
        self.bGuild = bGuild


class GameChannelReservation:
    def __init__(self, deck: sdbDeck.SDBDeck):
        self.deck = deck
        self.shutdownOverride = False
        self.shutdownOverrideReason = ""
        self.started = False


class GamePhase(Enum):
    setup = -1
    playRound = 0
    postRound = 1
    gameOver = 2


class SubmissionsProgressIndicator:
    def __init__(self, msg: Message, players: List[sdbPlayer.SDBPlayer]):
        self.msg = msg
        self.playerText = {p: "Choosing cards... " + cfg.defaultEmojis.loading.sendable for p in players if not p.isChooser}
        self.embed = lib.discordUtil.makeEmbed(authorName="Waiting For Submissions...", icon=EMPTY_IMAGE, col=Colour.gold())

    
    async def updateMsg(self):
        self.embed.description = "\n".join(p.dcUser.mention + ": " + t for p, t in self.playerText.items())
        await self.msg.edit(content=self.msg.content, embed=self.embed)


    async def submissionReceived(self, player: sdbPlayer.SDBPlayer, noUpdateMsg=False):
        self.playerText[player] = self.playerText[player][:-len(cfg.defaultEmojis.loading.sendable)] + cfg.defaultEmojis.submit.sendable
        if not noUpdateMsg:
            await self.updateMsg()

    
    async def playerJoin(self, player: sdbPlayer.SDBPlayer, noUpdateMsg=False):
        self.playerText[player] = "Choosing cards... " + cfg.defaultEmojis.loading.sendable
        if not noUpdateMsg:
            await self.updateMsg()

    
    async def playerLeave(self, player: sdbPlayer.SDBPlayer, noUpdateMsg=False):
        del self.playerText[player]
        if not noUpdateMsg:
            await self.updateMsg()
            

class SDBGame:
    def __init__(self, owner: Member, deck: sdbDeck.SDBDeck, activeExpansions: List[str], channel: TextChannel, rounds: int,
                    gamePhase : int = GamePhase.setup):
        self.owner = owner
        self.channel = channel
        self.deck = deck
        self.expansionNames = activeExpansions
        self.gamePhase = gamePhase
        self.players = []
        self.currentBlackCard = None
        self.shutdownOverride = False
        self.shutdownOverrideReason = ""
        self.started = False
        self.currentChooser = -1
        self.playersLeftDuringSetup = []
        self.rounds = rounds
        self.currentRound = 0
        self.maxPlayers = sum(len(deck.cards[expansion].white) for expansion in activeExpansions) // cfg.cardsPerHand
        self.waitingForSubmissions = False
        self.submissionsProgress = None
        self.deckUpdater: DeckUpdateRegistry = None
        self.allowNewMembers = True

        # self.configOptions = []
        # self.configOptions.append(sdbGameConfig.SDBOwnerOption(self))


    def allPlayersSubmitted(self):
        for player in self.players:
            if not player.isChooser and not player.hasSubmitted:
                return False
        return True


    async def setupPlayerHand(self, player):
        if self.shutdownOverride:
            return
        emptyCardEmbed = Embed()
        emptyCardEmbed.set_image(url=self.deck.emptyWhite.url)
        await lib.discordUtil.sendDM("```yaml\n" + self.owner.name + "'s game```\n<#" + str(self.channel.id) + ">\n\n__Your Hand__", player.dcUser, None, reactOnDM=False, exceptOnFail=True)
        for _ in range(cfg.cardsPerHand):
            if self.shutdownOverride:
                return
            cardSlotMsg = await player.dcUser.dm_channel.send("​", embed=emptyCardEmbed)
            cardSlot = sdbPlayer.SDBCardSlot(None, cardSlotMsg, player)
            player.hand.append(cardSlot)
            cardSelector = SDBCardSelector(cardSlotMsg, player, cardSlot)
            botState.reactionMenusDB[cardSlotMsg.id] = cardSelector
            await cardSelector.updateMessage()
            player.selectorMenus.append(cardSelector)
        
        playMenuMsg = await player.dcUser.dm_channel.send("​")
        player.playMenu = SDBCardPlayMenu(playMenuMsg, player)
        botState.reactionMenusDB[playMenuMsg.id] = player.playMenu
        await player.playMenu.updateMessage()


    async def setupAllPlayerHands(self):
        if self.shutdownOverride:
            return
        loadingMsg = await self.channel.send("Setting up player hands... " + cfg.defaultEmojis.loading.sendable)
        handDistributors = set()

        def scheduleHandDistributor(self, player):
            task = asyncio.ensure_future(self.setupPlayerHand(player))
            handDistributors.add(task)
            task.add_done_callback(handDistributors.remove)

        for player in self.players:
            scheduleHandDistributor(self, player)

        if handDistributors:
            await asyncio.wait(handDistributors)
        await loadingMsg.edit(content="Setting up player hands... " + cfg.defaultEmojis.submit.sendable)


    async def dealPlayerCards(self, player):
        if self.shutdownOverride:
            return
        for cardSlot in player.hand:
            if self.shutdownOverride:
                return
            if cardSlot.isEmpty:
                newCard = self.deck.randomWhite(self.expansionNames)
                # while player.hasCard(newCard):
                #     newCard = self.deck.randomWhite(self.expansionNames)
                await cardSlot.setCard(newCard)


    async def dealAllPlayerCards(self):
        if self.shutdownOverride:
            return
        loadingStr = "** **\n**__Round " + str(self.currentRound) + ((" of " + str(self.rounds)) if self.rounds != -1 else "") + "__**\nDealing cards... "
        loadingMsg = await self.channel.send(loadingStr + cfg.defaultEmojis.loading.sendable)

        cardDistributors = set()

        def scheduleCardDistributor(self, player):
            task = asyncio.ensure_future(self.dealPlayerCards(player))
            cardDistributors.add(task)
            task.add_done_callback(cardDistributors.remove)

        for player in self.players:
            scheduleCardDistributor(self, player)

        if cardDistributors:
            await asyncio.wait(cardDistributors)

        await loadingMsg.edit(content=loadingStr + cfg.defaultEmojis.submit.sendable)


    async def dcMemberJoinGame(self, member):
        player = sdbPlayer.SDBPlayer(member, self)
        await self.setupPlayerHand(player)
        await self.dealPlayerCards(player)
        await player.updatePlayMenu()
        self.players.append(player)
        if self.submissionsProgress is not None:
            await self.submissionsProgress.playerJoin(player)
        await self.channel.send(member.display_name + " joined the game!")


    async def setOwner(self, member, deleteOldCfgMenu=True):
        if deleteOldCfgMenu:
            try:
                currentPlayer = self.playerFromMember(self.owner)
            except KeyError:
                pass
            else:
                if currentPlayer.hasConfigMenu():
                    await currentPlayer.closeConfigMenu()
        self.owner = member
        await self.channel.send("The deck master is now  " + self.owner.mention + "! 🙇‍♂️")
        await self.owner.send("You are now deck master of the game in <#" + str(self.channel.id) + ">!\nThis means you are responsible for game admin, such as choosing to keep playing after every round.")


    async def cancelPlayerSelectorMenus(self, player):
        for menu in player.selectorMenus:
            await menu.delete()
        player.selectorMenus = []

    
    async def dcMemberLeaveGame(self, member):
        player = None
        for p in self.players:
            if p.dcUser == member:
                player = p
                break
        if not self.started:
            if player is not None:
                for slot in player.hand:
                    if not slot.isEmpty:
                        slot.currentCard.revoke()
                self.players.remove(player)
            await self.channel.send(member.mention + " left the game.")
            
            if (len(self.players) - len(self.playersLeftDuringSetup)) < 2:
                self.shutdownOverride = True
                self.shutdownOverrideReason = "There aren't enough players left to continue the game."
        else:
            if player is None:
                raise RuntimeError("Failed to find a matching player for member " + member.name + "#" + str(member.id))

            if self.gamePhase == GamePhase.setup:
                self.playersLeftDuringSetup.append(player)
            elif self.gamePhase == GamePhase.playRound:
                if player.isChooser:
                    newChooser = await self.setChooser()
                    if newChooser.hasSubmitted:
                        newChooser.submittedCards = []
                        newChooser.hasSubmitted = False
                    player.isChooser = False
                    await self.submissionsProgress.playerLeave(newChooser)
                elif self.submissionsProgress is not None:
                    await self.submissionsProgress.playerLeave(player)
                self.players.remove(player)
            elif self.gamePhase == GamePhase.postRound:
                if player.isChooser:
                    player.isChooser = False
                    await self.channel.send("The card chooser left the game! Please add any reaction to end the round. The winner will be chosen at random.")
                self.players.remove(player)
            else:
                self.players.remove(player)

            for slot in player.hand:
                if not slot.isEmpty:
                    slot.currentCard.revoke()
            await self.channel.send(member.mention + " left the game.")
            
            if (len(self.players) - len(self.playersLeftDuringSetup)) < 2:
                self.shutdownOverride = True
                self.shutdownOverrideReason = "There aren't enough players left to continue the game."

            elif self.owner == player.dcUser:
                newOwner = random.choice(self.players)
                while newOwner == player or newOwner in self.playersLeftDuringSetup:
                    newOwner = random.choice(self.players)
                await self.channel.send("The deck master has left the game!")
                await self.setOwner(newOwner.dcUser)
        
        if player is not None:
            await self.cancelPlayerSelectorMenus(player)


    async def doGameIntro(self):
        if self.shutdownOverride:
            return
        await self.channel.send("Welcome to Super Deck Breaker!")


    async def pickNewBlackCard(self):
        if self.shutdownOverride:
            return
        self.currentBlackCard = sdbPlayer.SDBCardSlot(None, await self.channel.send("​"), None)
        await self.currentBlackCard.setCard(self.deck.randomBlack(self.expansionNames))


    async def endWaitForSubmissions(self):
        self.waitingForSubmissions = False
        self.submissionsProgress = None
        await self.advanceGame()


    async def submissionReceived(self, player: sdbPlayer.SDBPlayer):
        if self.shutdownOverride:
            return
        await self.submissionsProgress.submissionReceived(player)
        if self.allPlayersSubmitted():
            await self.endWaitForSubmissions()


    async def startWaitForSubmissions(self):
        self.waitingForSubmissions = True
        self.submissionsProgress = SubmissionsProgressIndicator(await self.channel.send("Waiting for submissions..."),
                                                                self.players)
        await self.submissionsProgress.updateMsg()

        while self.waitingForSubmissions:
            await asyncio.sleep(cfg.timeouts.allSubmittedCheckPeriodSeconds)
            if self.shutdownOverride:
                return


    async def pickWinningCards(self):
        if self.shutdownOverride:
            return
        submissionsMenuMsg = await self.channel.send("The submissions are in! But who wins?")
        if cfg.submissionsPresentationMethod == "sequential" or self.currentBlackCard.currentCard.requiredWhiteCards == 1:
            menu = InlineSequentialSubmissionsReviewMenu(submissionsMenuMsg, self,
                                                    cfg.timeouts.submissionsReviewMenuSeconds)
        elif cfg.submissionsPresentationMethod == "merged":
            submissions = await SDBSubmissionsReviewMenu.buildMergedSubmissionsMenuImages(self)
            menu = SDBSubmissionsReviewMenu.InlineMergedSubmissionsReviewMenu(submissionsMenuMsg, submissions, cfg.timeouts.submissionsReviewMenuSeconds, self.getChooser())
        else:
            raise ValueError("Unknown submissionsPresentationMethod '" + str(cfg.submissionsPresentationMethod) + "'")
        try:
            winningOption = await menu.doMenu()
        except InvalidClosingReaction:
            winningPlayer = random.choice(self.players)
        else:
            if len(winningOption) != 1:
                raise RuntimeError("given selected options array of length " + str(len(winningOption)) + " but should be length 1")
            winningPlayer = winningOption[0].player

        winnerEmbed = lib.discordUtil.makeEmbed(titleTxt="Winning Submission", desc=winningPlayer.dcUser.mention)
        await submissionsMenuMsg.delete()

        if self.currentBlackCard.currentCard.requiredWhiteCards == 1:
            winnerEmbed.set_image(url=winningPlayer.submittedCards[0].url)
            await self.channel.send(winningPlayer.dcUser.mention + " wins the round!", embed=winnerEmbed)
        else:
            if cfg.submissionsPresentationMethod == "merged":
                if cfg.cardStorageMethod == "local":
                    roundCardsDir = cfg.paths.cardsTemp + os.sep + str(self.channel.id) + os.sep + str(self.currentRound)
                    winnerImagePath = SDBSubmissionsReviewMenu.mergedSubmissionImagePath(roundCardsDir, winningPlayer)
                    winnerImage = File(winnerImagePath, filename="winning-submission.jpg")
                    winnerEmbed.set_image(url="attachment://winning-submission.jpg")
                    await self.channel.send(winningPlayer.dcUser.mention + " wins the round!", file=winnerImage, embed=winnerEmbed)

                    if os.path.isdir(roundCardsDir):
                        shutil.rmtree(roundCardsDir)
                else:
                    winnerEmbed.set_image(url=submissions[winningPlayer])
                    await self.channel.send(winningPlayer.dcUser.mention + " wins the round!", embed=winnerEmbed)
            else:
                roundCardsDir = cfg.paths.cardsTemp + os.sep + str(self.channel.id) + os.sep + str(self.currentRound)
                if os.path.isdir(roundCardsDir):
                    shutil.rmtree(roundCardsDir)
                os.makedirs(roundCardsDir)

                winnerImagePath = SDBSubmissionsReviewMenu.mergedSubmissionImagePath(roundCardsDir, winningPlayer)
                winnerImage = await SDBSubmissionsReviewMenu.mergePlayerSubmissions(winningPlayer)
                winnerImage.save(winnerImagePath)
                winnerImage.close()

                winnerImage = File(winnerImagePath, filename="winning-submission.jpg")
                winnerEmbed.set_image(url="attachment://winning-submission.jpg")
                await self.channel.send(winningPlayer.dcUser.mention + " wins the round!", file=winnerImage, embed=winnerEmbed)

                if os.path.isdir(roundCardsDir):
                    shutil.rmtree(roundCardsDir)
            
        winningPlayer.points += 1


    async def _resetPlayerSubmissions(self, player: sdbPlayer.SDBPlayer):
        player.hasSubmitted = False
        player.submittedCards = []
        await player.updatePlayMenu()
        await player.removeErrs()


    async def resetSubmissions(self):
        if self.shutdownOverride:
            return

        tasks = set()

        def scheduleSubmissionsReset(self, player):
            task = asyncio.ensure_future(self._resetPlayerSubmissions(player))
            tasks.add(task)
            task.add_done_callback(tasks.remove)

        for player in self.players:
            scheduleSubmissionsReset(self, player)

        if tasks:
            await asyncio.wait(tasks)


    async def showLeaderboard(self):
        leaderboardEmbed = Embed()
        for player in self.players:
            leaderboardEmbed.add_field(name=player.dcUser.display_name, value=str(player.points))
        await self.channel.send(embed=leaderboardEmbed)


    async def checkKeepPlaying(self):
        if self.shutdownOverride:
            return False
        if self.rounds != -1:
            return self.currentRound <= self.rounds
        else:
            confirmMsg = await self.channel.send("Play another round?")
            keepPlaying = await InlineConfirmationMenu(confirmMsg, self.owner, cfg.timeouts.keepPlayingMenuSeconds).doMenu()
            await confirmMsg.delete()
            return cfg.defaultEmojis.accept in keepPlaying


    async def endGame(self):
        callingBGuild = botState.guildsDB.getGuild(self.channel.guild.id)
        if self.channel in callingBGuild.runningGames:
            del callingBGuild.runningGames[self.channel]
        winningplayers = [self.players[0]]
        for player in self.players[1:]:
            if player.points > winningplayers[0].points:
                winningplayers = [player]
            elif player.points == winningplayers[0].points:
                winningplayers.append(player)

        resultsEmbed = lib.discordUtil.makeEmbed(titleTxt="Thanks For Playing!",
                                                    desc="Congats to the winner" + ("" if len(winningplayers) == 1 else "s") +
                                                    ", with " + str(winningplayers[0].points) + " point" +
                                                    (("" if winningplayers[0].points == 1 else "s")) +
                                                    (("" if len(winningplayers) == 1 else " each") + "!"))
        resultsEmbed.add_field(name="🏆 Winner" + ("" if len(winningplayers) == 1 else "s"), value=", ".join(player.dcUser.mention for player in winningplayers))

        if self.shutdownOverride:
            await self.channel.send(self.shutdownOverrideReason if self.shutdownOverrideReason else "The game was forcibly ended, likely due to an error.", embed=resultsEmbed)
        else:
            await self.channel.send(embed=resultsEmbed)

        for player in self.players:
            await self.cancelPlayerSelectorMenus(player)

        if self.deckUpdater is not None and self.deckUpdater.bGuild.decks[self.deck.name]["last_update"] == -1:
            for game in callingBGuild.runningGames.values():
                if game.deck.name == self.deck.name:
                    return
            self.deckUpdater.bGuild.decks[self.deck.name]["last_update"] = datetime.utcnow().timestamp()
            await sdbDeck.updateDeck(self.deckUpdater.callingMsg, self.deckUpdater.bGuild, self.deck.name)


    def getChooser(self):
        return self.players[self.currentChooser]


    async def setChooser(self):
        if self.shutdownOverride:
            return
        self.getChooser().isChooser = False
        self.currentChooser = (self.currentChooser + 1) % len(self.players)
        newChooser = self.getChooser()
        newChooser.isChooser = True
        await self.channel.send(self.getChooser().dcUser.mention + " is now the card chooser!")
        return newChooser


    async def playPhase(self):
        keepPlaying = True
        waitForSubmissions = False

        if self.gamePhase == GamePhase.setup:
            self.currentRound += 1
            await self.dealAllPlayerCards()
            await self.pickNewBlackCard()
            await self.setChooser()
            await self.resetSubmissions()
            
        elif self.gamePhase == GamePhase.playRound:
            if self.getChooser() in self.playersLeftDuringSetup:
                await self.setChooser()
                await self.resetSubmissions()
            for leftPlayer in self.playersLeftDuringSetup:
                self.players.remove(leftPlayer)
            self.playersLeftDuringSetup = []
            waitForSubmissions = True
            await self.startWaitForSubmissions()

        elif self.gamePhase == GamePhase.postRound:
            await self.pickWinningCards()

        elif self.gamePhase == GamePhase.gameOver:
            await self.showLeaderboard()
            keepPlaying = await self.checkKeepPlaying()

        if keepPlaying and not self.shutdownOverride and not waitForSubmissions:
            await self.advanceGame()
        elif self.shutdownOverride or not keepPlaying:
            await self.endGame()


    async def advanceGame(self):
        if self.gamePhase == GamePhase.setup:
            self.gamePhase = GamePhase.playRound

        elif self.gamePhase == GamePhase.playRound:
            self.gamePhase = GamePhase.postRound

        elif self.gamePhase == GamePhase.postRound:
            self.gamePhase = GamePhase.gameOver

        elif self.gamePhase == GamePhase.gameOver:
            self.gamePhase = GamePhase.setup

        await self.playPhase()


    async def startGame(self):
        self.currentChooser = random.randint(0, len(self.players) - 1)
        self.players[self.currentChooser].isChooser = True
        await self.doGameIntro()
        await self.setOwner(self.owner, deleteOldCfgMenu=False)
        await self.setupAllPlayerHands()
        self.started = True
        await self.playPhase()


    def playerFromMember(self, member):
        for player in self.players:
            if player.dcUser == member:
                return player
        raise KeyError("No player for member " + member.name + "#" + str(member.id))


    def hasDCMember(self, member):
        try:
            self.playerFromMember(member)
        except KeyError:
            return False
        return True


    async def redealPlayer(self, player):
        if player.hasRedealt:
            raise ValueError("The given player has already redealt this game: " + player.dcUser.name + "#" + str(player.dcUser.id))
        player.hasRedealt = True
        for slot in player.hand:
            if not slot.isEmpty:
                await slot.removeCard(self.deck.emptyWhite, updateMessage = False)
        await self.dealPlayerCards(player)


async def startGameFromExpansionMenu(gameCfg : Dict[str, Union[str, int]]):
    if gameCfg["menuID"] in botState.reactionMenusDB:
        menu = botState.reactionMenusDB[gameCfg["menuID"]]
        playChannel = menu.msg.channel
        callingBGuild = botState.guildsDB.getGuild(menu.msg.guild.id)

        if playChannel not in callingBGuild.runningGames:
            await playChannel.send("The game was forcibly ended, likely due to an error.")
        elif callingBGuild.runningGames[playChannel].shutdownOverride:
            reservation = callingBGuild.runningGames[playChannel]
            await playChannel.send(reservation.shutdownOverrideReason if reservation.shutdownOverrideReason else "The game was forcibly ended, likely due to an error.")
            await expiryFunctions.deleteReactionMenu(menu.msg.id)
            if playChannel in callingBGuild.runningGames:
                del callingBGuild.runningGames[playChannel]
        elif callingBGuild.decks[gameCfg["deckName"]]["updating"]:
            await expiryFunctions.deleteReactionMenu(menu.msg.id)
            if playChannel in callingBGuild.runningGames:
                del callingBGuild.runningGames[playChannel]
            await playChannel.send("Game cancelled - someone is updating the deck!")

        if menu.currentMaxPlayers < cfg.minPlayerCount:
            await playChannel.send(":x: You don't have enough white cards!\nPlease select at least " + str(cfg.minPlayerCount * cfg.cardsPerHand) + " white cards.")
        elif not menu.hasBlackCardsSelected:
            await playChannel.send(":x: You don't have enough black cards!\nPlease select at least one black card.")
        else:
            rounds = gameCfg["rounds"]

            expansionNames = [option.name for option in menu.selectedOptions if menu.selectedOptions[option]]
            await expiryFunctions.deleteReactionMenu(menu.msg.id)
            if playChannel in callingBGuild.runningGames:
                del callingBGuild.runningGames[playChannel]

            await callingBGuild.startGameSignups(menu.targetMember, playChannel, gameCfg["deckName"], expansionNames, rounds)
    else:
        botState.logger.log("sdbGame", "startGameFromExpansionMenu", "menu not in reactionMenusDB: " + str(gameCfg["menuID"]), category="reactionMenus", eventType="MENU_NOTFOUND")
