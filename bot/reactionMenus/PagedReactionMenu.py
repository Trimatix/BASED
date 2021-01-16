from datetime import datetime
from ..users import basedUser
from . import ReactionMenu, expiryFunctions
from discord import Message, Member, Role, Embed, Colour
from .. import lib, botState
from typing import Any, Dict, List
from ..scheduling import TimedTask
from ..cfg import cfg
import asyncio
from types import FunctionType


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

        nextOption = ReactionMenu.NonSaveableReactionMenuOption("Next Page", cfg.defaultEmojis.next, self.nextPage, None)
        prevOption = ReactionMenu.NonSaveableReactionMenuOption("Previous Page", cfg.defaultEmojis.previous, self.previousPage, None)

        self.firstPageControls = {  cfg.defaultEmojis.next:      nextOption}

        self.midPageControls = {    cfg.defaultEmojis.next:      nextOption,
                                    cfg.defaultEmojis.previous:  prevOption}

        self.lastPageControls = {   cfg.defaultEmojis.previous:  prevOption}

        self.onePageControls = {}

        if not noCancel:
            cancelOption = ReactionMenu.NonSaveableReactionMenuOption("Close Menu", cfg.defaultEmojis.cancel, self.delete, None)
            for optionsDict in [self.firstPageControls, self.midPageControls, self.lastPageControls, self.onePageControls]:
                optionsDict[cfg.defaultEmojis.cancel] = cancelOption

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
            await self.msg.remove_reaction(cfg.defaultEmojis.next.sendable, botState.client.user)
        if self.currentPageNum == 1:
            await self.msg.add_reaction(cfg.defaultEmojis.previous.sendable)


    async def previousPage(self):
        if self.currentPageNum == 0:
            raise RuntimeError("Attempted to previousPage while on the first page")
        self.currentPageNum -= 1
        self.updateCurrentPage()
        await self.updateMessage(noRefreshOptions=True)
        if self.currentPageNum == 0:
            self.msg = await self.msg.channel.fetch_message(self.msg.id)
            await self.msg.remove_reaction(cfg.defaultEmojis.previous.sendable, botState.client.user)
        if self.currentPageNum == len(self.pages) - 2:
            await self.msg.add_reaction(cfg.defaultEmojis.next.sendable)

    
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
                    await self.msg.remove_reaction(cfg.defaultEmojis.previous.sendable, botState.client.user)
                if self.currentPageNum != len(self.pages) - 1:
                    await self.msg.add_reaction(cfg.defaultEmojis.next.sendable)


class MultiPageOptionPicker(PagedReactionMenu):
    def __init__(self, msg : Message, pages : Dict[Embed, Dict[lib.emojis.BasedEmoji, ReactionMenu.NonSaveableSelecterMenuOption]] = {}, 
                    timeout : TimedTask.TimedTask = None, targetMember : Member = None, targetRole : Role = None, owningBasedUser : basedUser.BasedUser = None):
        
        controls = {cfg.defaultEmojis.accept: ReactionMenu.NonSaveableReactionMenuOption("Submit", cfg.defaultEmojis.accept, self.delete, None),
                    cfg.defaultEmojis.cancel: ReactionMenu.NonSaveableReactionMenuOption("Cancel Game", cfg.defaultEmojis.cancel, expiryFunctions.deleteReactionMenu, msg.id),
                    cfg.defaultEmojis.spiral: ReactionMenu.NonSaveableReactionMenuOption("Toggle All", cfg.defaultEmojis.spiral,
                                                                                                addFunc=ReactionMenu.selectorSelectAllOptions, addArgs=msg.id,
                                                                                                removeFunc=ReactionMenu.selectorDeselectAllOptions, removeArgs=msg.id)
        }
        self.selectedOptions = {}
        for pageOptions in pages.values():
            for option in pageOptions.values():
                if option.emoji not in controls:
                    self.selectedOptions[option] = False

        for pageEmbed in pages:
            for controlEmoji in controls:
                if controlEmoji not in pages[pageEmbed]:
                    pages[pageEmbed][controlEmoji] = controls[controlEmoji]

        super().__init__(msg, pages=pages, timeout=timeout, targetMember=targetMember, targetRole=targetRole, owningBasedUser=owningBasedUser, noCancel=True)


    async def updateSelectionsField(self):
        newSelectedStr = ", ".join(option.name for option in self.selectedOptions if self.selectedOptions[option])
        newSelectedStr = newSelectedStr if newSelectedStr else "​"

        for pageEmbed in self.pages:
            for fieldIndex in range(len(pageEmbed.fields)):
                field = pageEmbed.fields[fieldIndex]
                if field.name == "Currently selected:":
                    pageEmbed.set_field_at(fieldIndex, name=field.name, value=newSelectedStr, inline=False)
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
                    noCancel : bool = False, returnTriggers : List[ReactionMenu.ReactionMenuOption] = [], anon: bool = False):
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


# class InlineMultiPageOptionPicker(InlinePagedReactionMenu):
#     def __init__(self, msg: Message, timeoutSeconds: int, pages: Dict[Embed, Dict[lib.emojis.BasedEmoji, ReactionMenu.ReactionMenuOption]], targetMember: Member, targetRole: Role, owningBasedUser: basedUser.BasedUser, noCancel: bool, returnTriggers: List[lib.emojis.BasedEmoji], anon: bool):

#     def __init__(self, msg : Message, pages : Dict[Embed, Dict[lib.emojis.BasedEmoji, ReactionMenu.NonSaveableSelecterMenuOption]] = {}, 
#                     timeout : TimedTask.TimedTask = None, targetMember : Member = None, targetRole : Role = None, owningBasedUser : basedUser.BasedUser = None):
        
#         controls = {cfg.defaultEmojis.accept: ReactionMenu.NonSaveableReactionMenuOption("Submit", cfg.defaultEmojis.accept, self.delete, None),
#                     cfg.defaultEmojis.cancel: ReactionMenu.NonSaveableReactionMenuOption("Cancel Game", cfg.defaultEmojis.cancel, expiryFunctions.deleteReactionMenu, msg.id),
#                     cfg.defaultEmojis.spiral: ReactionMenu.NonSaveableReactionMenuOption("Toggle All", cfg.defaultEmojis.spiral,
#                                                                                                 addFunc=ReactionMenu.selectorSelectAllOptions, addArgs=msg.id,
#                                                                                                 removeFunc=ReactionMenu.selectorDeselectAllOptions, removeArgs=msg.id)
#         }
#         self.selectedOptions = {}
#         for pageOptions in pages.values():
#             for option in pageOptions.values():
#                 if option.emoji not in controls:
#                     self.selectedOptions[option] = False

#         for pageEmbed in pages:
#             for controlEmoji in controls:
#                 if controlEmoji not in pages[pageEmbed]:
#                     pages[pageEmbed][controlEmoji] = controls[controlEmoji]

#         super().__init__(msg, timeoutSeconds, pages=pages, targetMember=targetMember, targetRole=targetRole, owningBasedUser=owningBasedUser, noCancel=True, returnTriggers=returnTriggers, anon=anon)


#     async def updateSelectionsField(self):
#         newSelectedStr = ", ".join(option.name for option in self.selectedOptions if self.selectedOptions[option])
#         newSelectedStr = newSelectedStr if newSelectedStr else "​"

#         for pageEmbed in self.pages:
#             for fieldIndex in range(len(pageEmbed.fields)):
#                 field = pageEmbed.fields[fieldIndex]
#                 if field.name == "Currently selected:":
#                     pageEmbed.set_field_at(fieldIndex, name=field.name, value=newSelectedStr)
#                 break

#         await self.updateMessage(noRefreshOptions=True)


class NonSaveableValuedMenuOption(ReactionMenu.NonSaveableReactionMenuOption):
    def __init__(self, name: str, emoji: lib.emojis.BasedEmoji, value: Any, addFunc: FunctionType = None, addArgs = None, removeFunc: FunctionType = None, removeArgs = None):
        super().__init__(name, emoji, addFunc=addFunc, addArgs=addArgs, removeFunc=removeFunc, removeArgs=removeArgs)
        self.value = value


def makeTemplatePagedMenuPages(items: Dict[str, Any]) -> Dict[Embed, Dict[lib.emojis.BasedEmoji, NonSaveableValuedMenuOption]]:
    numPages = int((len(items) - 1) / cfg.defaultOptionsPerPage) + 1
    optionKeys = list(items.keys())
    pages = {}
    for pageNum in range(numPages):
        pageEmbed = Embed()
        pages[pageEmbed] = {}
        if pageNum == numPages - 1:
            pageOptionNamesIndices = range(pageNum, min(len(items), pageNum + cfg.defaultOptionsPerPage))
        else:
            pageOptionNamesIndices = range(pageNum, pageNum + cfg.defaultOptionsPerPage)
        for optionIndex in pageOptionNamesIndices:
            optionName = optionKeys[optionIndex]
            optionEmoji = cfg.defaultEmojis.menuOptions[optionIndex]
            pages[pageEmbed][optionEmoji] = NonSaveableValuedMenuOption(optionName, optionEmoji, items[optionName])
            pageEmbed.add_field(name=optionEmoji.sendable + " : " + optionName, value="​", inline=False)
    
    return pages
