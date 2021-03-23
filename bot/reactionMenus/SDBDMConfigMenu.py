from bot import botState
from . import reactionMenu, pagedReactionMenu, confirmationReactionMenu
from discord import Message, Member, Role, Embed, User
from typing import Dict, Union
from .. import lib
from ..scheduling import timedTask
from ..users import basedUser
from ..game import sdbGame
import random
from ..cfg import cfg
from typing import Set, Dict
from discord.embeds import EmbedProxy, Embed
import asyncio


class ToggleOption:
    def __init__(self, state, name, trueDesc, falseDesc, emoji):
        self.state = state
        self.name = name
        self.trueDesc = trueDesc
        self.falseDesc = falseDesc
        self.emoji = emoji
        if state:
            self.desc = cfg.defaultEmojis.optionEnabled.sendable + " " + trueDesc
        else:
            self.desc = cfg.defaultEmojis.optionDisabled.sendable + " " + falseDesc

    
    def toggle(self):
        if self.state:
            self.state = False
            self.desc = cfg.defaultEmojis.optionDisabled.sendable + " " + self.falseDesc
        else:
            self.state = True
            self.desc = cfg.defaultEmojis.optionEnabled.sendable + " " + self.trueDesc


class SDBDMConfigMenu(pagedReactionMenu.PagedReactionMenu):
    def __init__(self, msg: Message, game: "sdbGame.SDBGame"):
        self.game = game
        self.paused = False
        pageOneEmbed = Embed()
        self.errorFields: Dict[Embed, Set[EmbedProxy]] = {pageOneEmbed: set()}
        self.hasErrs = False
        pages = {pageOneEmbed: {}}
        pageOneEmbed.title = "Deck Master Admin Menu"
        ownerEmoji = lib.emojis.BasedEmoji(unicode="👑")
        roundsEmoji = lib.emojis.BasedEmoji(unicode="⌚")
        endGameEmoji = lib.emojis.BasedEmoji(unicode="🗑")
        self.newPlayerToggle = ToggleOption(False, "Lock Player Count", "New players will not be allowed to join.", "New players are allowed to join.", lib.emojis.BasedEmoji(unicode="🔐"))
        pageOneEmbed.add_field(name=ownerEmoji.sendable + " : Relinquish Deck Master", value="Hand game ownership to another user.")
        pageOneEmbed.add_field(name=roundsEmoji.sendable + " : Change Number of Rounds", value="Change the number of rounds in the game, or switch to free play.")
        pageOneEmbed.add_field(name=endGameEmoji.sendable + " : End Game", value="End the game now.")
        pageOneEmbed.add_field(name=self.newPlayerToggle.emoji.sendable + " : " + self.newPlayerToggle.name, value=self.newPlayerToggle.desc)
        pages[pageOneEmbed][ownerEmoji] = reactionMenu.NonSaveableReactionMenuOption("Relinquish Deck Master", ownerEmoji, addFunc=self.reliquishOwner)
        pages[pageOneEmbed][roundsEmoji] = reactionMenu.NonSaveableReactionMenuOption("Change Number of Rounds", roundsEmoji, addFunc=self.changeNumRounds)
        pages[pageOneEmbed][endGameEmoji] = reactionMenu.NonSaveableReactionMenuOption("End Game", endGameEmoji, addFunc=self.endGame)
        pages[pageOneEmbed][self.newPlayerToggle.emoji] = reactionMenu.NonSaveableReactionMenuOption(self.newPlayerToggle.name, self.newPlayerToggle.emoji, addFunc=self.toggleNewPlayerLock)
        super().__init__(msg, pages=pages, targetMember=game.owner)


    async def reactionAdded(self, emoji: lib.emojis.BasedEmoji, member: Union[Member, User]):
        if not self.paused:
            return await super().reactionAdded(emoji, member)


    async def reactionRemoved(self, emoji: lib.emojis.BasedEmoji, member: Union[Member, User]):
        if not self.paused:
            return await super().reactionRemoved(emoji, member)


    def _removeErrs(self):
        for pageNum, page in enumerate(self.errorFields):
            for field in self.errorFields[page]:
                if field in page.fields:
                    page.fields.remove(field)
                else:
                    botState.logger.log("SDBDMConfigMenu", "_removeErrs", "Failed to find error field '" + field.name + "' in page " + str(pageNum),
                                        category="reactionMenus", eventType="UKWN_ERR")
                self.errorFields[page].remove(field)
        self.hasErrs = False


    async def _addErr(self, name, desc, noUpdateMsg=False):
        self.hasErrs = True
        self.currentPage.add_field(name=name, value=desc, inline=False)
        self.errorFields[self.currentPage].add(self.currentPage.fields[-1])
        if not noUpdateMsg:
            await self.updateMessage(noRefreshOptions=True)


    async def pauseMenu(self):
        self.paused = True
        self.currentPage.set_footer(text="[menu paused]")
        if self.hasErrs:
            self._removeErrs()
        await self.updateMessage(noRefreshOptions=True)


    async def unpauseMenu(self):
        self.paused = False
        self.currentPage.set_footer(text=Embed.Empty)
        if self.hasErrs:
            self._removeErrs()
        await self.updateMessage(noRefreshOptions=True)


    async def reliquishOwner(self):
        await self.pauseMenu()
        playerPickerMsg = await lib.discordUtil.sendDM("​", self.game.owner, self.msg, reactOnDM=False)
        newOwner = None
        if playerPickerMsg is not None:
            pages = pagedReactionMenu.makeTemplatePagedMenuPages({str(player.dcUser): player.dcUser for player in self.game.players if player.dcUser != self.game.owner})
            for pageEmbed in pages:
                randomPlayerOption = pagedReactionMenu.NonSaveableValuedMenuOption("Pick Random Player", cfg.defaultEmojis.spiral, None)
                pages[pageEmbed][cfg.defaultEmojis.spiral] = randomPlayerOption
                pageEmbed.add_field(name=cfg.defaultEmojis.spiral.sendable + " : Pick Random Player", value="​", inline=False)
                pageEmbed.title = "New Deck Master"
                pageEmbed.description = "Who should be the new deck master?"
                pageEmbed.set_footer(text="This menu will expire in " + str(cfg.timeouts.sdbPlayerSelectorSeconds) + "s")

            allOptions = []
            for page in pages.values():
                allOptions += [option for option in page.values()]

            try:
                playerSelection = await pagedReactionMenu.InlinePagedReactionMenu(playerPickerMsg, cfg.timeouts.sdbPlayerSelectorSeconds, pages=pages, targetMember=self.game.owner, noCancel=True, returnTriggers=allOptions).doMenu()
            except pagedReactionMenu.InvalidClosingReaction as e:
                await self.game.channel.send("An unexpected error occurred when picking the new deck master.\nPicking one at random...")
                botState.logger.log("SDBDMConfigMenu", "relinquishOwner", "Invalid closing reaction: " + e.emoji.sendable, category="reactionMenus", eventType="InvalidClosingReaction")
            else:
                if playerSelection != [] and playerSelection[0] != cfg.defaultEmojis.spiral: 
                    newOwner = playerSelection[0].value
            
            await playerPickerMsg.delete()
        else:
            await self.game.channel.send(self.owner.mention + " Player selection menu failed to send! Are your DMs open?\nPicking a new deck master at random...")
        
        if newOwner is None:
            newOwner = random.choice(self.game.players).dcUser
            while newOwner == self.game.owner:
                print("random picking")
                newOwner = random.choice(self.game.players).dcUser

        await self.game.setOwner(newOwner)


    async def changeNumRounds(self):
        if self.game.currentRound > cfg.roundsPickerOptions[-1]:
            await self._addErr("Can't change game length", "Too many rounds have passed! Please start a new game.")
        else:
            await self.pauseMenu()
            options = {}
            optionRounds = {}
            optNum = 0
            for numRounds in cfg.roundsPickerOptions:
                if numRounds != self.game.rounds and numRounds >= self.game.currentRound:
                    emoji = cfg.defaultEmojis.menuOptions[optNum]
                    optionRounds[emoji] = numRounds
                    options[emoji] = reactionMenu.DummyReactionMenuOption("Best of " + str(numRounds), emoji)
                    optNum += 1
            if self.game.rounds != -1:
                options[cfg.defaultEmojis.spiral] = reactionMenu.DummyReactionMenuOption("Free play", cfg.defaultEmojis.spiral)
            options[cfg.defaultEmojis.cancel] = reactionMenu.DummyReactionMenuOption("Cancel", cfg.defaultEmojis.cancel)

            roundsPickerMsg = await self.msg.channel.send("​")
            currentRoundsStr = "**Free play**" if self.game.rounds == -1 else "**Best of " + str(self.game.rounds) + "**"
            roundsResult = await reactionMenu.InlineReactionMenu(roundsPickerMsg, self.game.owner, cfg.timeouts.numRoundsPickerSeconds,
                                                            options=options, returnTriggers=list(options.keys()), titleTxt="Game Length",
                                                            desc="How many rounds would you like to play?\nCurrent setting: " + currentRoundsStr,
                                                            footerTxt="This menu will expire in " + str(cfg.timeouts.numRoundsPickerSeconds) + "s").doMenu()

            rounds = cfg.defaultSDBRounds
            pickerCancelled = False
            if len(roundsResult) == 1:
                if roundsResult[0] == cfg.defaultEmojis.spiral:
                    rounds = -1
                elif roundsResult[0] == cfg.defaultEmojis.cancel:
                    pickerCancelled = True
                else:
                    rounds = optionRounds[roundsResult[0]]
            if not pickerCancelled:
                self.game.rounds = rounds
                await self.game.channel.send("🃏 The deck master enabled **Free play** mode!" if rounds == -1 else \
                                            "🃏 The deck master changed the game to **best of " + str(rounds) + "!**")
            asyncio.ensure_future(roundsPickerMsg.delete())
            await self.unpauseMenu()


    async def endGame(self):
        await self.pauseMenu()
        confirmMsg = await self.msg.channel.send("​")
        endConfirmMenu = await confirmationReactionMenu.InlineConfirmationMenu(confirmMsg, self.game.owner, cfg.timeouts.numRoundsPickerSeconds,
                                                                                authorName="Confirm Game End", icon=botState.client.user.avatar_url_as(size=32),
                                                                                desc="Are you sure you want to end the game now?").doMenu()
        if len(endConfirmMenu) > 0 and endConfirmMenu[0] == cfg.defaultEmojis.accept:
            self.game.shutdownOverride = True
            self.game.shutdownOverrideReason = "The game was ended by the deck master."
            await self.msg.channel.send("Ending game...")
        else:
            asyncio.ensure_future(confirmMsg.delete())
            await self.unpauseMenu()


    async def toggleNewPlayerLock(self):
        self.newPlayerToggle.toggle()
        self.game.allowNewPlayers = not self.newPlayerToggle.state
        for page in self.pages:
            for fieldNum, field in enumerate(page.fields):
                if field.name == self.newPlayerToggle.emoji.sendable + " : " + self.newPlayerToggle.name:
                    page.set_field_at(fieldNum, name=self.newPlayerToggle.emoji.sendable + " : " + self.newPlayerToggle.name, value=self.newPlayerToggle.desc)
        self._removeErrs()
        await self.updateMessage(noRefreshOptions=True)
        