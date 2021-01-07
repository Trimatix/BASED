from datetime import datetime
from ..users import basedUser
from . import ReactionMenu, expiryFunctions
from discord import Message, Member, Role, Embed, Colour
from .. import lib, botState
from typing import Dict, List
from ..scheduling import TimedTask
from ..cfg import cfg
import asyncio


async def menuJumpToPage(data : dict):
    await botState.reactionMenusDB[data["menuID"]].jumpToPage(data["pageNum"])


class PagedReactionMenu(ReactionMenu.ReactionMenu):
    """A reaction menu that, instead of taking a list of options, takes a list of pages of options.
    """
    saveable = False
    
    def __init__(self, msg : Message, pages : Dict[Embed, Dict[lib.emojis.BasedEmoji, ReactionMenu.ReactionMenuOption]] = {}, 
                    timeout : TimedTask.TimedTask = None, targetMember : Member = None, targetRole : Role = None, owningBasedUser : basedUser.BasedUser = None,
                    noCancel : bool = False, anon: bool = False):
        """
        :param discord.Message msg: the message where this menu is embedded
        :param pages: A dictionary associating embeds with pages, where each page is a dictionary storing all options on that page and their behaviour (Default {})
        :type pages: dict[Embed, dict[lib.emojis.BasedEmoji, ReactionMenuOption]]
        :param TimedTask timeout: The TimedTask responsible for expiring this menu (Default None)
        :param discord.Member targetMember: The only discord.Member that is able to interact with this menu. All other reactions are ignored (Default None)
        :param discord.Role targetRole: In order to interact with this menu, users must possess this role. All other reactions are ignored (Default None)
        :param BasedUser owningBasedUser: The user who initiated this menu. No built in behaviour. (Default None)
        """
        super().__init__(msg, anon=anon)

        self.pages = pages
        self.msg = msg
        self.currentPageNum = 0
        self.currentPage = None
        self.currentPageControls = {}
        self.timeout = timeout
        self.targetMember = targetMember
        self.targetRole = targetRole
        self.owningBasedUser = owningBasedUser

        nextOption = ReactionMenu.NonSaveableReactionMenuOption("Next Page", cfg.defaultNextEmoji, self.nextPage, None)
        prevOption = ReactionMenu.NonSaveableReactionMenuOption("Previous Page", cfg.defaultPreviousEmoji, self.previousPage, None)

        self.firstPageControls = {  cfg.defaultNextEmoji:      nextOption}

        self.midPageControls = {    cfg.defaultNextEmoji:      nextOption,
                                    cfg.defaultPreviousEmoji:  prevOption}

        self.lastPageControls = {   cfg.defaultPreviousEmoji:  prevOption}

        self.onePageControls = {}

        if not noCancel:
            cancelOption = ReactionMenu.NonSaveableReactionMenuOption("Close Menu", cfg.defaultCancelEmoji, self.delete, None)
            for optionsDict in [self.firstPageControls, self.midPageControls, self.lastPageControls, self.onePageControls]:
                optionsDict[cfg.defaultCancelEmoji] = cancelOption

        if len(self.pages) == 1:
            self.currentPageControls = self.onePageControls
        self.updateCurrentPage()


    def getMenuEmbed(self) -> Embed:
        """Generate the discord.Embed representing the reaction menu, and that
        should be embedded into the menu's message.
        This will usually contain a short description of the menu, its options, and its expiry time.

        :return: A discord.Embed representing the menu and its options
        :rtype: discord.Embed 
        """
        return self.currentPage


    def updateCurrentPage(self):
        self.currentPage = list(self.pages.keys())[self.currentPageNum]
        self.options = list(self.pages.values())[self.currentPageNum]

        if len(self.pages) > 1:
            if self.currentPageNum == len(self.pages) - 1:
                self.currentPageControls = self.lastPageControls
            elif self.currentPageNum == 0:
                self.currentPageControls = self.firstPageControls
            else:
                self.currentPageControls = self.midPageControls

        for optionEmoji in self.currentPageControls:
            self.options[optionEmoji] = self.currentPageControls[optionEmoji]


    async def nextPage(self):
        if self.currentPageNum == len(self.pages) - 1:
            raise RuntimeError("Attempted to nextPage while on the last page")
        self.currentPageNum += 1
        self.updateCurrentPage()
        await self.updateMessage(noRefreshOptions=True)
        if self.currentPageNum == len(self.pages) - 1:
            self.msg = await self.msg.channel.fetch_message(self.msg.id)
            await self.msg.remove_reaction(cfg.defaultNextEmoji.sendable, botState.client.user)
        if self.currentPageNum == 1:
            await self.msg.add_reaction(cfg.defaultPreviousEmoji.sendable)


    async def previousPage(self):
        if self.currentPageNum == 0:
            raise RuntimeError("Attempted to previousPage while on the first page")
        self.currentPageNum -= 1
        self.updateCurrentPage()
        await self.updateMessage(noRefreshOptions=True)
        if self.currentPageNum == 0:
            self.msg = await self.msg.channel.fetch_message(self.msg.id)
            await self.msg.remove_reaction(cfg.defaultPreviousEmoji.sendable, botState.client.user)
        if self.currentPageNum == len(self.pages) - 2:
            await self.msg.add_reaction(cfg.defaultNextEmoji.sendable)

    
    async def jumpToPage(self, pageNum : int):
        if pageNum < 0 or pageNum > len(self.pages) - 1:
            raise IndexError("Page number out of range: " + str(pageNum))
        if pageNum != self.currentPageNum:
            self.currentPageNum = pageNum
            self.updateCurrentPage()
            await self.updateMessage(noRefreshOptions=True)
            if len(self.pages) > 1:
                if self.currentPageNum == 0:
                    self.msg = await self.msg.channel.fetch_message(self.msg.id)
                    await self.msg.remove_reaction(cfg.defaultPreviousEmoji.sendable, botState.client.user)
                if self.currentPageNum != len(self.pages) - 1:
                    await self.msg.add_reaction(cfg.defaultNextEmoji.sendable)


class MultiPageOptionPicker(PagedReactionMenu):
    def __init__(self, msg : Message, pages : Dict[Embed, Dict[lib.emojis.BasedEmoji, ReactionMenu.NonSaveableSelecterMenuOption]] = {}, 
                    timeout : TimedTask.TimedTask = None, targetMember : Member = None, targetRole : Role = None, owningBasedUser : basedUser.BasedUser = None):
        
        self.selectedOptions = {}
        for pageOptions in pages.values():
            for option in pageOptions.values():
                self.selectedOptions[option] = False

        for pageEmbed in pages:
            if cfg.defaultAcceptEmoji not in pages[pageEmbed]:
                pages[pageEmbed][cfg.defaultAcceptEmoji] = ReactionMenu.NonSaveableReactionMenuOption("Submit", cfg.defaultAcceptEmoji, self.delete, None)

            if cfg.defaultCancelEmoji not in pages[pageEmbed]:
                pages[pageEmbed][cfg.defaultCancelEmoji] = ReactionMenu.NonSaveableReactionMenuOption("Cancel Game", cfg.defaultCancelEmoji, expiryFunctions.deleteReactionMenu, msg.id)

            if cfg.spiralEmoji not in pages[pageEmbed]:
                pages[pageEmbed][cfg.spiralEmoji] = ReactionMenu.NonSaveableReactionMenuOption("Toggle All", cfg.spiralEmoji,
                                                                                                addFunc=ReactionMenu.selectorSelectAllOptions, addArgs=msg.id,
                                                                                                removeFunc=ReactionMenu.selectorDeselectAllOptions, removeArgs=msg.id)

        super().__init__(msg, pages=pages, timeout=timeout, targetMember=targetMember, targetRole=targetRole, owningBasedUser=owningBasedUser, noCancel=True)


    async def updateSelectionsField(self):
        newSelectedStr = ", ".join(option.name for option in self.selectedOptions if self.selectedOptions[option])
        newSelectedStr = newSelectedStr if newSelectedStr else "​"

        for pageEmbed in self.pages:
            for fieldIndex in range(len(pageEmbed.fields)):
                field = pageEmbed.fields[fieldIndex]
                if field.name == "Currently selected:":
                    pageEmbed.set_field_at(fieldIndex, name=field.name, value=newSelectedStr)
                break

        await self.updateMessage(noRefreshOptions=True)


class InvalidClosingReaction(Exception):
    def __init__(self, emoji, *args: object) -> None:
        self.emoji = emoji
        super().__init__(*args)



class InlinePagedReactionMenu(PagedReactionMenu):
    """A reaction menu that, instead of taking a list of options, takes a list of pages of options.
    """
    saveable = False
    
    def __init__(self, msg : Message, timeoutSeconds : int, pages : Dict[Embed, Dict[lib.emojis.BasedEmoji, ReactionMenu.ReactionMenuOption]] = {}, 
                    targetMember : Member = None, targetRole : Role = None, owningBasedUser : basedUser.BasedUser = None,
                    noCancel : bool = False, returnTriggers : List[lib.emojis.BasedEmoji] = [], anon: bool = False):
        """
        :param discord.Message msg: the message where this menu is embedded
        :param int timeoutSeconds: The number of seconds until this menu expires
        :param returnTriggers: List of menu options that trigger the returning of the menu (default [])
        :type returnTriggers: List[ReactionMenu.ReactionMenuOption]
        :param pages: A dictionary associating embeds with pages, where each page is a dictionary storing all options on that page and their behaviour (Default {})
        :type pages: dict[Embed, dict[lib.emojis.BasedEmoji, ReactionMenuOption]]
        :param discord.Member targetMember: The only discord.Member that is able to interact with this menu. All other reactions are ignored (Default None)
        :param discord.Role targetRole: In order to interact with this menu, users must possess this role. All other reactions are ignored (Default None)
        :param BasedUser owningBasedUser: The user who initiated this menu. No built in behaviour. (Default None)
        """
        super().__init__(msg, pages=pages, timeout=None, targetMember=targetMember, targetRole=targetRole, owningBasedUser=owningBasedUser, noCancel=noCancel, anon=anon)
        self.menuActive = True
        self.timeoutSeconds = timeoutSeconds
        self.returnTriggers = returnTriggers


    async def reactionClosesMenu(self, reactPL):
        # if reactPL.guild_id is None:
        #     user = botState.client.get_user(reactPL.user_id)
        # else:
        #     user = botState.client.get_guild(reactPL.guild_id).get_member(reactPL.user_id)
        #     if user is None:
        #         guild = await botState.client.fetch_guild(reactPL.guild_id)
        #         user = guild.get_member(reactPL.user_id)

        # emoji = lib.emojis.BasedEmoji.fromReaction(reactPL.emoji, rejectInvalid=True)

        _, user, emoji = await lib.discordUtil.reactionFromRaw(reactPL)

        if user is None:
            botState.logger.log(type(self).__name__, "reactionClosesMenu", "Failed to get user #" + str(reactPL.user_id), category="reactionMenus", eventType="USRFAIL")
            return False
        if emoji is None:
            botState.logger.log(type(self).__name__, "reactionClosesMenu", "Failed to get emoji: " + str(reactPL.emoji), category="reactionMenus", eventType="EMOJIFAIL")
            return False

        if emoji not in self.pages[self.currentPage]:
            return False

        if self.targetMember is not None and reactPL.user_id != self.targetMember.id:
            return False

        if self.targetRole is not None:
            if None in [reactPL.guild_id, user] or self.targetRole not in user.roles:
                return False
        
        return self.pages[self.currentPage][emoji] in self.returnTriggers


    def reactionValid(self, reactPL):
        if reactPL.guild_id is None:
            user = botState.client.get_user(reactPL.user_id)
        else:
            user = botState.client.get_guild(reactPL.guild_id).get_member(reactPL.user_id)
            # if user is None:
            #     guild = await botState.client.fetch_guild(reactPL.guild_id)
            #     user = guild.get_member(reactPL.user_id)

        emoji = lib.emojis.BasedEmoji.fromReaction(reactPL.emoji, rejectInvalid=True)


        # _, user, emoji = await lib.discordUtil.reactionFromRaw(reactPL)

        if user is None:
            botState.logger.log(type(self).__name__, "reactionClosesMenu", "Failed to get user #" + str(reactPL.user_id), category="reactionMenus", eventType="USRFAIL")
            return False
        if emoji is None:
            botState.logger.log(type(self).__name__, "reactionClosesMenu", "Failed to get emoji: " + str(reactPL.emoji), category="reactionMenus", eventType="EMOJIFAIL")
            return False

        if emoji not in self.pages[self.currentPage]:
            return False

        if self.targetMember is not None and reactPL.user_id != self.targetMember.id:
            return False

        if self.targetRole is not None:
            if None in [reactPL.guild_id, user] or self.targetRole not in user.roles:
                return False
        
        # if reactPL.event_type == "REACTION_ADD":
        #     await self.reactionAdded(emoji, user)
        # else:
        #     await self.reactionRemoved(emoji, user)

        return True


    async def doMenu(self):
        await self.updateMessage()
        timeoutLeft = self.timeoutSeconds
        
        while self.menuActive:
            try:
                prev = datetime.utcnow()
                reactPL = await lib.discordUtil.clientMultiWaitFor(["raw_reaction_add", "raw_reaction_remove"], timeoutLeft, check=self.reactionValid)
                _, user, emoji = await lib.discordUtil.reactionFromRaw(reactPL)
                if reactPL.event_type == "REACTION_ADD":
                    await self.reactionAdded(emoji, user)
                else:
                    await self.reactionRemoved(emoji, user)

                timeoutLeft -= (datetime.utcnow() - prev).seconds

                if await self.reactionClosesMenu(reactPL):
                    currentEmbed = self.currentPage
                    currentEmbed.set_footer(text="This menu has now expired.")
                    await self.msg.edit(embed=currentEmbed)
                    if emoji in self.pages[self.currentPage]:
                        return [self.pages[self.currentPage][emoji]]
                    raise InvalidClosingReaction(emoji)

            except asyncio.TimeoutError:
                await self.msg.edit(content="This menu has now expired. Please try the command again.")
                return []
