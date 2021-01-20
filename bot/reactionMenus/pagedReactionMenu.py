from ..users import basedUser
from .import reactionMenu
from discord import Message, Member, Role, Embed
from .. import lib, botState
from typing import Dict
from ..scheduling import timedTask
from ..cfg import cfg


async def menuJumpToPage(data: dict):
    await botState.reactionMenusDB[data["menuID"]].jumpToPage(data["pageNum"])


class PagedReactionMenu(reactionMenu.ReactionMenu):
    """A reaction menu that, instead of taking a list of options, takes a list of pages of options.
    """
    saveable = False

    def __init__(self, msg: Message, pages: Dict[Embed, Dict[lib.emojis.BasedEmoji, reactionMenu.ReactionMenuOption]] = None,
                 timeout: timedTask.TimedTask = None, targetMember: Member = None, targetRole: Role = None,
                 owningBasedUser: basedUser.BasedUser = None):
        """
        :param discord.Message msg: the message where this menu is embedded
        :param pages: A dictionary associating embeds with pages, where each page is a dictionary
                        storing all options on that page and their behaviour (Default {})
        :type pages: dict[Embed, dict[lib.emojis.BasedEmoji, ReactionMenuOption]]
        :param TimedTask timeout: The TimedTask responsible for expiring this menu (Default None)
        :param discord.Member targetMember: The only discord.Member that is able to interact with this menu.
                                            All other reactions are ignored (Default None)
        :param discord.Role targetRole: In order to interact with this menu, users must possess this role.
                                            All other reactions are ignored (Default None)
        :param BasedUser owningBasedUser: The user who initiated this menu. No built in behaviour. (Default None)
        """

        self.pages = pages if pages is not None else {}
        self.msg = msg
        self.currentPageNum = 0
        self.currentPage = None
        self.currentPageControls = {}
        self.timeout = timeout
        self.targetMember = targetMember
        self.targetRole = targetRole
        self.owningBasedUser = owningBasedUser

        nextOption = reactionMenu.NonSaveableReactionMenuOption("Next Page", cfg.defaultEmojis.next,
                                                                self.nextPage, None)
        prevOption = reactionMenu.NonSaveableReactionMenuOption("Previous Page", cfg.defaultEmojis.previous,
                                                                self.previousPage, None)
        cancelOption = reactionMenu.NonSaveableReactionMenuOption("Close Menu", cfg.defaultEmojis.cancel,
                                                                self.delete, None)

        self.firstPageControls = {cfg.defaultEmojis.cancel: cancelOption,
                                  cfg.defaultEmojis.next: nextOption}

        self.midPageControls = {cfg.defaultEmojis.cancel: cancelOption,
                                cfg.defaultEmojis.next: nextOption,
                                cfg.defaultEmojis.previous: prevOption}

        self.lastPageControls = {cfg.defaultEmojis.cancel: cancelOption,
                                 cfg.defaultEmojis.previous: prevOption}

        self.onePageControls = {cfg.defaultEmojis.cancel: cancelOption}

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
        """Update the menu's options and controls for the current page.
        """
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
        """Set the menu to display the next page.

        :raise RuntimeError: When the current page is the last page
        """
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
        """Set the menu to display the previous page.

        :raise RuntimeError: When the current page is the first page
        """
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


    async def jumpToPage(self, pageNum: int):
        """Set the menu to display the given page number.

        :param int pageNum: the zero-based index of the page to display
        :raise IndexError: If the given page number is out of range
        """
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
