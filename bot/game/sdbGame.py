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


class GamePhase(Enum):
    setup = -1
    playRound = 0
    # postRound = 1
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
        self.started = False
        self.currentChooser = -1


    def allPlayersSubmitted(self):
        for player in self.players:
            if not player.hasSubmitted:
                return False
        return True


    async def doGameIntro(self):
        await self.channel.send("")


    async def setupPlayerHand(self, player):
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
        loadingMsg = await self.channel.send("Setting up player hands... " + cfg.loadingEmoji.sendable)
        for player in self.players:
            await self.setupPlayerHand(player)
        await loadingMsg.edit(content="Setting up player hands... " + cfg.defaultSubmitEmoji.sendable)


    async def dealPlayerCards(self, player):
        for cardSlot in player.hand:
            if cardSlot.isEmpty:
                newCard = self.deck.randomWhite(self.expansionNames)
                # while player.hasCard(newCard):
                #     newCard = self.deck.randomWhite(self.expansionNames)
                await cardSlot.setCard(newCard)


    async def dealAllPlayerCards(self):
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


    async def doGameIntro(self):
        await self.channel.send("Welcome to Super Deck Breaker!")


    async def pickNewBlackCard(self):
        self.currentBlackCard = sdbPlayer.SDBCardSlot(None, await self.channel.send("​"), None)
        await self.currentBlackCard.setCard(self.deck.randomBlack(self.expansionNames))


    async def waitForSubmissions(self):
        waitingMsg = await self.channel.send("Waiting for submissions...")
        while not self.allPlayersSubmitted():
            await asyncio.sleep(cfg.submissionWaitingPeriod)
        await waitingMsg.delete()


    async def pickWinningCards(self):
        submissionsMenuMsg = await self.channel.send("The submissions are in! But who wins?")
        menu = InlineSDBSubmissionsReviewMenu(submissionsMenuMsg, self.players,
                                                cfg.submissionsReviewMenuTimeout,
                                                self.currentBlackCard.currentCard.requiredWhiteCards > 1,
                                                self.owner)
        winningOption = await menu.doMenu()
        if len(winningOption) != 1:
            raise RuntimeError("given selected options array of length " + str(len(winningOption)) + " but should be length 1")
        winningOption[0].player.points += 1


    async def resetSubmissions(self):
        for player in self.players:
            player.hasSubmitted = False
            await player.updatePlayMenu()


    async def showLeaderboard(self):
        leaderboardEmbed = Embed()
        for player in self.players:
            leaderboardEmbed.add_field(name=player.dcUser.display_name, value=str(player.points))
        await self.channel.send(embed=leaderboardEmbed)


    async def checkKeepPlaying(self):
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
        await self.channel.send(embed=resultsEmbed)


    def getChooser(self):
        return self.players[self.currentChooser]


    async def setChooser(self):
        self.getChooser().isChooser = False
        self.currentChooser = (self.currentChooser + 1) % len(self.players)
        await self.channel.send(self.getChooser().dcUser.mention + " is now the card chooser!")


    async def playPhase(self):
        keepPlaying = True

        if self.gamePhase == GamePhase.setup:
            await self.dealAllPlayerCards()
            await self.pickNewBlackCard()
            await self.setChooser()
            await self.resetSubmissions()
            
        elif self.gamePhase == GamePhase.playRound:
            await self.waitForSubmissions()
            await self.pickWinningCards()

        # elif self.gamePhase == GamePhase.postRound:
        #     await self.dealCards()

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
            self.gamePhase = GamePhase.gameOver

        # elif self.gamePhase == GamePhase.postRound:
        #     self.gamePhase = GamePhase.setup

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