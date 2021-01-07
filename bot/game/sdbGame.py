from discord.embeds import Embed
from .. import botState, lib
from typing import Dict, Union
from ..reactionMenus import expiryFunctions
from ..baseClasses.enum import Enum
from ..cfg import cfg
from . import sdbPlayer, sdbDeck
import asyncio
from ..reactionMenus.SDBSubmissionsReviewMenu import InlineSDBSubmissionsReviewMenu
from ..reactionMenus.ConfirmationReactionMenu import InlineConfirmationMenu
from ..reactionMenus.SDBCardPlayMenu import SDBCardPlayMenu
from ..reactionMenus.SDBCardSelector import SDBCardSelector
from ..reactionMenus.PagedReactionMenu import InvalidClosingReaction
import random


class GamePhase(Enum):
    setup = -1
    playRound = 0
    postRound = 1
    gameOver = 2


class SDBGame:
    def __init__(self, owner, deck, activeExpansions, channel, gamePhase=GamePhase.setup):
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


    def allPlayersSubmitted(self):
        for player in self.players:
            if not player.isChooser and not player.hasSubmitted:
                return False
        return True


    async def setupPlayerHand(self, player):
        if self.shutdownOverride:
            return
        await lib.discordUtil.sendDM("```yaml\n" + self.owner.name + "'s game```\n<#" + str(self.channel.id) + ">\n\n__Your Hand__", player.dcUser, None, reactOnDM=False, exceptOnFail=True)
        for _ in range(cfg.cardsPerHand):
            cardSlotMsg = await player.dcUser.dm_channel.send("​")
            cardSlot = sdbPlayer.SDBCardSlot(None, cardSlotMsg, player)
            player.hand.append(cardSlot)
            cardSelector = SDBCardSelector(cardSlotMsg, player, cardSlot)
            botState.reactionMenusDB[cardSlotMsg.id] = cardSelector
            await cardSelector.updateMessage()
        
        playMenuMsg = await player.dcUser.dm_channel.send("​")
        player.playMenu = SDBCardPlayMenu(playMenuMsg, player)
        botState.reactionMenusDB[playMenuMsg.id] = player.playMenu
        await player.playMenu.updateMessage()


    async def setupAllPlayerHands(self):
        if self.shutdownOverride:
            return
        loadingMsg = await self.channel.send("Setting up player hands... " + cfg.loadingEmoji.sendable)
        for player in self.players:
            await self.setupPlayerHand(player)
        await loadingMsg.edit(content="Setting up player hands... " + cfg.defaultSubmitEmoji.sendable)


    async def dealPlayerCards(self, player):
        if self.shutdownOverride:
            return
        for cardSlot in player.hand:
            if cardSlot.isEmpty:
                newCard = self.deck.randomWhite(self.expansionNames)
                # while player.hasCard(newCard):
                #     newCard = self.deck.randomWhite(self.expansionNames)
                await cardSlot.setCard(newCard)


    async def dealAllPlayerCards(self):
        if self.shutdownOverride:
            return
        loadingMsg = await self.channel.send("Dealing cards... " + cfg.loadingEmoji.sendable)
        for player in self.players:
            await self.dealPlayerCards(player)
        await loadingMsg.edit(content="Dealing cards... " + cfg.defaultSubmitEmoji.sendable)


    async def dcMemberJoinGame(self, member):
        player = sdbPlayer.SDBPlayer(member, self)
        await self.setupPlayerHand(player)
        await self.dealPlayerCards(player)
        await player.updatePlayMenu()
        self.players.append(player)
        await self.channel.send(member.display_name + " joined the game!")

    
    async def dcMemberLeaveGame(self, member):
        player = None
        for p in self.players:
            if p.dcUser == member:
                player = p
                break
        if player is None:
            raise RuntimeError("Failed to find a matching player for member " + member.name + "#" + str(member.id))

        if self.gamePhase == GamePhase.setup:
            self.playersLeftDuringSetup.append(player)
        elif self.gamePhase == GamePhase.playRound:
            if player.isChooser:
                await self.setChooser()
                if self.getChooser().hasSubmitted:
                    self.getChooser().submittedCards = []
                    self.getChooser().hasSubmitted = False
                player.isChooser = False
            self.players.remove(player)
        elif self.gamePhase == GamePhase.postRound:
            if player.isChooser:
                player.isChooser = False
                await self.channel.send("The card chooser left the game! Please add any reaction to end the round. The winner will be chosen at random.")
            self.players.remove(player)
        else:
            self.players.remove(player)

        for slot in player.hand:
            slot.currentCard.revoke()
        await self.channel.send(player.dcUser.mention + " left the game.")
        
        if len(self.players) < 2:
            self.shutdownOverride = True
            self.shutdownOverrideReason = "There aren't enough players left to continue the game."


    async def doGameIntro(self):
        if self.shutdownOverride:
            return
        await self.channel.send("Welcome to Super Deck Breaker!")


    async def pickNewBlackCard(self):
        if self.shutdownOverride:
            return
        self.currentBlackCard = sdbPlayer.SDBCardSlot(None, await self.channel.send("​"), None)
        await self.currentBlackCard.setCard(self.deck.randomBlack(self.expansionNames))


    async def waitForSubmissions(self):
        if self.shutdownOverride:
            return
        waitingMsg = await self.channel.send("Waiting for submissions...")
        while not self.allPlayersSubmitted() and not self.shutdownOverride:
            await asyncio.sleep(cfg.submissionWaitingPeriod)
        await waitingMsg.delete()


    async def pickWinningCards(self):
        if self.shutdownOverride:
            return
        submissionsMenuMsg = await self.channel.send("The submissions are in! But who wins?")
        menu = InlineSDBSubmissionsReviewMenu(submissionsMenuMsg, self,
                                                cfg.submissionsReviewMenuTimeout,
                                                self.currentBlackCard.currentCard.requiredWhiteCards > 1,
                                                self.owner,
                                                self.getChooser())
        try:
            winningOption = await menu.doMenu()
        except InvalidClosingReaction:
            winningPlayer = random.choice(self.players)
        else:
            if len(winningOption) != 1:
                raise RuntimeError("given selected options array of length " + str(len(winningOption)) + " but should be length 1")
            winningPlayer = winningOption[0].player

        await self.channel.send(winningPlayer.dcUser.mention + " wins the round!")
        winningPlayer.points += 1


    async def resetSubmissions(self):
        if self.shutdownOverride:
            return
        for player in self.players:
            player.hasSubmitted = False
            await player.updatePlayMenu()


    async def showLeaderboard(self):
        leaderboardEmbed = Embed()
        for player in self.players:
            leaderboardEmbed.add_field(name=player.dcUser.display_name, value=str(player.points))
        await self.channel.send(embed=leaderboardEmbed)


    async def checkKeepPlaying(self):
        if self.shutdownOverride:
            return
        confirmMsg = await self.channel.send("Play another round?")
        keepPlaying = await InlineConfirmationMenu(confirmMsg, self.owner, cfg.keepPlayingConfirmMenuTimeout).doMenu()
        await confirmMsg.delete()
        return cfg.defaultAcceptEmoji in keepPlaying


    async def endGame(self):
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
        resultsEmbed.add_field(name="Winner" + ("" if len(winningplayers) == 1 else "s"), value=", ".join(player.dcUser.mention for player in winningplayers))
        if self.shutdownOverride:
            await self.channel.send(self.shutdownOverrideReason if self.shutdownOverrideReason else "The game was forcibly ended, likely due to an error.", embed=resultsEmbed)
        else:
            await self.channel.send(embed=resultsEmbed)


    def getChooser(self):
        return self.players[self.currentChooser]


    async def setChooser(self):
        if self.shutdownOverride:
            return
        self.getChooser().isChooser = False
        self.currentChooser = (self.currentChooser + 1) % len(self.players)
        self.getChooser().isChooser = True
        await self.channel.send(self.getChooser().dcUser.mention + " is now the card chooser!")


    async def playPhase(self):
        keepPlaying = True

        if self.gamePhase == GamePhase.setup:
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

            await self.waitForSubmissions()

        elif self.gamePhase == GamePhase.postRound:
            await self.pickWinningCards()

        elif self.gamePhase == GamePhase.gameOver:
            await self.showLeaderboard()
            keepPlaying = await self.checkKeepPlaying()

        if keepPlaying and not self.shutdownOverride:
            await self.advanceGame()
        else:
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
        self.currentChooser = -1
        self.players[-1].isChooser = True
        await self.doGameIntro()
        await self.setupAllPlayerHands()
        self.started = True
        await self.playPhase()


    def hasDCMember(self, member):
        for player in self.players:
            if player.dcUser == member:
                return True
        return False


async def startGameFromExpansionMenu(gameCfg : Dict[str, Union[str, int]]):
    menu = botState.reactionMenusDB[gameCfg["menuID"]]
    callingBGuild = botState.guildsDB.getGuild(menu.msg.guild.id)
    playChannel = menu.msg.channel

    expansionNames = [option.name for option in menu.selectedOptions if menu.selectedOptions[option]]
    if not expansionNames:
        await playChannel.send(":x: You didn't select any expansion packs!")

    if playChannel in callingBGuild.runningGames:
        del callingBGuild.runningGames[playChannel]
    
    await expiryFunctions.deleteReactionMenu(menu.msg.id)
    await callingBGuild.startGameSignups(menu.targetMember, playChannel, gameCfg["deckName"], expansionNames)