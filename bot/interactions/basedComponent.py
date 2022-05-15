import asyncio
from inspect import iscoroutinefunction
from discord import ButtonStyle, Embed, Client, app_commands, Component
from discord.errors import HTTPException, NotFound
from discord import Message, Interaction
from discord.ui import View, Button
from discord.utils import MISSING

from typing import Awaitable, Dict, Iterable, List, Union, MutableSet, Callable, Coroutine

from .. import botState, lib
from ..cfg import cfg
from . import basedApp


class StaticComponentMeta:
    def __init__(self, category: str, subCategory: str = None, args: str = None) -> None:
        self.category = category
        self.subCategory = subCategory or None
        self.args = args or None


class StaticComponentCallbackMeta:
    def __init__(self, category: str, subCategory: str = None) -> None:
        self.category = category
        self.subCategory = subCategory or None


def validateParam(paramName: str, val: str):
    if cfg.staticComponentCustomIdSeparator in val:
        raise ValueError(f"Invalid {paramName} '{val}' - cannot contain reserved character '{cfg.staticComponentCustomIdSeparator}'")


def validateCustomId(customId: str):
    if len(customId) > 100:
        raise ValueError(f"Resulting custom_id is too long. The combined length of category, subCategory and args must be less than {100 - len(cfg.staticComponentCustomIdPrefix) - 2 * len(cfg.staticComponentCustomIdSeparator)} characters")


def staticComponentCallback(
    *,
    category: str = "",
    subCategory: str = ""
):
    def decorator(func, category=category, subCategory=subCategory):
        if not iscoroutinefunction(func):
            raise TypeError("Decorator can only be applied to coroutines")
        if not category:
            raise ValueError("Missing required argument: category")

        validateParam("category", category)
        validateParam("subCategory", subCategory)
        
        basedApp.basedApp(func, basedApp.BasedAppType.StaticComponent)
        setattr(func, "__static_component_meta__", (category, subCategory))

        return func

    return decorator


def staticComponentCallbackMeta(callback: "basedApp.CallBackType") -> StaticComponentCallbackMeta:
    if basedApp.appType(callback) != basedApp.BasedAppType.StaticComponent:
        raise TypeError("The callback is not a static component callback")
    return StaticComponentCallbackMeta(*callback.__static_component_meta__)


def staticComponentCustomId(category: str, subCategory: str = "", args: str = "") -> str:
    validateParam("category", category)
    validateParam("subCategory", subCategory)
    validateParam("args", args)
    customId = cfg.staticComponentCustomIdPrefix + category + cfg.staticComponentCustomIdSeparator + (subCategory or "")
    if args:
        customId += cfg.staticComponentCustomIdSeparator + args
    validateCustomId(customId)
    return customId


def staticComponent(component: Component, category: str, subCategory: str = "", args: str = "") -> Component:
    if not hasattr(component, "custom_id"):
        raise ValueError(f"component type {type(component).__name__} cannot be static. Must have a custom_id")
    component.custom_id = staticComponentCustomId(category, subCategory, args)
    return component


def staticComponentKey(category: str, subCategory: str = "") -> str:
    key = cfg.staticComponentCustomIdPrefix + category + cfg.staticComponentCustomIdSeparator + (subCategory or "")
    validateCustomId(key)
    return key


def customIdIsStaticComponent(customId: str) -> bool:
    return customId.startswith(cfg.staticComponentCustomIdPrefix)


def staticComponentMeta(customId: str) -> StaticComponentMeta:
    if not customIdIsStaticComponent(customId):
        raise ValueError("customId does not represent a static component")
    rest = customId[len(cfg.staticComponentCustomIdPrefix):]
    split = rest.split(cfg.staticComponentCustomIdSeparator)
    return StaticComponentMeta(*split)


async def maybeDefer(interaction: Interaction, ephemeral: bool = False, thinking: bool = False):
    if not interaction.response._responded:
        await interaction.response.defer(ephemeral=ephemeral, thinking=thinking)


async def editWithFallback(interaction: Interaction, msg: Message, *args, **kwargs):
    if interaction.response._responded:
        await msg.edit(*args, **kwargs)
    else:
        await interaction.edit_original_message(*args, **kwargs)


class Menu:
    def __init__(self, view: View, embed: Embed):
        self.view = view
        self.embed = embed


def callbackWithChecks(callback: Union[Callable[[Interaction], bool], Callable[[Interaction], Awaitable[bool]]], *checks: Union[Callable[[Interaction], bool], Callable[[Interaction], Awaitable[bool]]]) -> Callable[[Interaction], Awaitable]:
    async def callback(interaction: Interaction):
        for check in checks:
            result = check(interaction)
            if isinstance(result, Awaitable):
                result = await result
            if not isinstance(result, bool):
                raise TypeError(f"check returned a non-bool ({type(result).__name__}) result: {result}. Not executing callback")
            if not result:
                await interaction.response.edit_message()
        isinstance(checks[0](interaction), Awaitable)
        cbResult = callback(interaction)
        if isinstance(cbResult, Awaitable):
            await cbResult


class PagedMultiButtonMenu:
    def __init__(self, pages: List[Menu], currentPageEmbed: Embed = None, currentPageNum: int = None, controlsCheck: Callable[[Interaction], bool] = None):
        self.pages = pages

        # Infer current page number and embed from kwargs (if any)
        if currentPageEmbed is None:
            self.currentPageNum = currentPageNum or 1
            self.menuEmbed = self.embedForPageNum(self.currentPageNum)
        if currentPageNum is None:
            if currentPageEmbed is None:
                self.currentPageNum = 1
                self.menuEmbed = self.embedForFirstPage()
            else:
                self.menuEmbed = currentPageEmbed
                self.currentPageNum = pages.index(currentPageEmbed) + 1
        
        if len(pages) > 1:
            forwardCanCall = lambda x: self.currentPageNum < self.lastPageNum() and controlsCheck(x)
            backwardCanCall = lambda x: self.currentPageNum > 1 and controlsCheck(x)
            self.forwardComponent = Button(ButtonStyle.blue, emoji=cfg.defaultEmojis.next.sendable, disabled=True)
            self.forwardComponent.callback = callbackWithChecks(self.nextPage, forwardCanCall)
            self.backwardComponent = Button(ButtonStyle.blue, emoji=cfg.defaultEmojis.previous.sendable, disabled=True)
            self.forwardComponent.callback = callbackWithChecks(self.previousPage, backwardCanCall)
            pageControls = [self.backwardComponent, self.forwardComponent]
            # These will be re-enabled on updateCurrentPage as appropriate
        else:
            self.forwardComponent = None
            self.backwardComponent = None
            pageControls = []

        if pageControls:
            
            for page in self.pages:
                for control in pageControls:
                    page.view.add_item(control)

        self.updateCurrentPage()


    def embedForPageNum(self, pageNum: int) -> Embed:
        return self.pages[pageNum - 1].embed


    def lastPageNum(self) -> int:
        return len(self.pages)


    def embedForLastPage(self) -> Embed:
        return self.embedForPageNum(self.lastPageNum())


    def embedForFirstPage(self) -> Embed:
        return self.embedForPageNum(1)


    def updateCurrentPage(self):
        """Update the menu's options and controls for the current page.
        """
        if len(self.pages) > 1:
            if self.currentPageNum == 1:
                if not self.backwardComponent.isDisabled():
                    self.backwardComponent.disable()
                if self.forwardComponent.isDisabled():
                    self.forwardComponent.enable()
            elif self.currentPageNum == self.lastPageNum():
                if not self.forwardComponent.isDisabled():
                    self.forwardComponent.disable()
                if self.backwardComponent.isDisabled():
                    self.backwardComponent.enable()
            else:
                if self.forwardComponent.isDisabled():
                    self.forwardComponent.enable()
                if self.backwardComponent.isDisabled():
                    self.backwardComponent.enable()

        self.menuEmbed = self.embedForPageNum(self.currentPageNum)
        self.buttons = self.buttonsOnPageEmbed(self.menuEmbed)


    async def nextPage(self):
        """Set the menu to display the next page.

        :raise lib.exceptions.PageOutOfRange: When the current page is the last page
        """
        if self.currentPageNum == self.lastPageNum():
            raise lib.exceptions.PageOutOfRange("Attempted to nextPage while on the last page")
        self.currentPageNum += 1
        self.updateCurrentPage()
        await self.updateMessage()


    async def previousPage(self):
        """Set the menu to display the previous page.

        :raise lib.exceptions.PageOutOfRange: When the current page is the first page
        """
        if self.currentPageNum == 0:
            raise lib.exceptions.PageOutOfRange("Attempted to previousPage while on the first page")
        self.currentPageNum -= 1
        self.updateCurrentPage()
        await self.updateMessage()


    async def jumpToPage(self, pageNum: int):
        """Set the menu to display the given page number.

        :param int pageNum: the zero-based index of the page to display
        :raise lib.exceptions.PageOutOfRange: If the given page number is out of range
        """
        if pageNum < 0 or pageNum > self.lastPageNum():
            raise lib.exceptions.PageOutOfRange("Page number out of range: " + str(pageNum))
        if pageNum != self.currentPageNum:
            self.currentPageNum = pageNum
            self.updateCurrentPage()
            await self.updateMessage()


# class PagedOptionPicker(PagedMultiButtonMenu):
#     def __init__(self, msg: Message, pages: Dict[Embed, List[BasedComponent]], submitRespond: Coroutine, currentPageEmbed: Embed = None, currentPageNum: int = None,
#                     noCancel: bool = None, cancelRespond: Coroutine = None, controlsCanCall: Callable[[ComponentContext], bool] = None,
#                     submitCanCall: Callable[[ComponentContext], bool] = None, unselectables: MutableSet[BasedComponent] = None,
#                     controlsUseEmoji: bool = True, selectControlsUseEmoji: bool = True, register: bool = True) -> None:

#         self.submitComponent = BasedComponent_InstancedBehaviour(create_button(ButtonStyle.green, emoji=cfg.defaultEmojis.submit.sendable if selectControlsUseEmoji else None, label=None if selectControlsUseEmoji else "Submit"), submitRespond, submitCanCall) #emoji=cfg.defaultEmojis.accept.sendable
#         self.toggleAllComponent = BasedComponent_InstancedBehaviour(create_button(ButtonStyle.blurple, emoji=cfg.defaultEmojis.spiral.sendable if selectControlsUseEmoji else None, label=None if selectControlsUseEmoji else "Toggle All"), self.toggleAll) #emoji=cfg.defaultEmojis.spiral.sendable

#         self.selectedOptions: Dict[BasedComponent, bool] = {}
#         self.optionIDs: Dict[str, BasedComponent] = {}

#         for pageOptions in pages.values():
#             for option in pageOptions:
#                 if not unselectables or option not in unselectables:
#                     self.selectedOptions[option] = False
#                     self.optionIDs[option.custom_id] = option
#             pageOptions += [self.toggleAllComponent, self.submitComponent]

#         super().__init__(msg, pages, currentPageEmbed=currentPageEmbed, currentPageNum=currentPageNum, noCancel=noCancel, cancelRespond=cancelRespond, controlsCanCall=controlsCanCall, controlsUseEmoji=controlsUseEmoji, register=register,
#                             returnTriggers=(self.submitComponent,))


#     async def updateSelectionsField(self, ctx: ComponentContext = None):
#         newSelectedStr = ", ".join(option.data['label'] for option in self.selectedOptions if self.selectedOptions[option])
#         newSelectedStr = newSelectedStr or "​"

#         for pageEmbed in self.pages:
#             for fieldIndex in range(len(pageEmbed.fields)):
#                 field = pageEmbed.fields[fieldIndex]
#                 if field.name == "Currently selected:":
#                     pageEmbed.set_field_at(fieldIndex, name=field.name, value=newSelectedStr, inline=False)
#                 break
        
#         await self.updateMessage(ctx=ctx)


#     async def toggleAll(self, ctx: ComponentContext = None):
#         if self.toggleAllComponent.data['style'] == ButtonStyle.green:
#             newSel, newCol = False, ButtonStyle.blurple
#         else:
#             newSel, newCol = True, ButtonStyle.green

#         for option in self.selectedOptions:
#             self.selectedOptions[option] = newSel
#         self.toggleAllComponent.data['style'] = newCol

#         await self.updateSelectionsField(ctx=ctx)


#     async def toggleOption(self, ctx: ComponentContext = None):
#         component = self.optionIDs[ctx.custom_id]
#         self.selectedOptions[component] = not self.selectedOptions[component]
#         await self.updateSelectionsField(ctx=ctx)
