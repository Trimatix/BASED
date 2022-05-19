from inspect import iscoroutinefunction
from discord import ButtonStyle, Embed, Component
from discord import Message, Interaction
from discord.ui import View, Button

from typing import Awaitable, List, TypeVar, Union, Callable

from .. import lib
from ..cfg import cfg
from . import basedApp


class StaticComponentMeta:
    """Data class carrying metadata about a static component.

    :var category: The category of the static component
    :type category: str
    :var subCategory: The sub-category of the static component
    :type subCategory: Optional[str]
    :var args: Arguments for this instance of the static component, to be passed to the callback
    :type args: Optional[str]
    """
    def __init__(self, category: str, subCategory: str = None, args: str = None) -> None:
        self.category = category
        self.subCategory = subCategory or None
        self.args = args or None


class StaticComponentCallbackMeta:
    """Data class carrying metadata about the callback coroutine for a static component.

    :var category: The category of the static component
    :type category: str
    :var subCategory: The sub-category of the static component
    :type subCategory: Optional[str]
    """
    def __init__(self, category: str, subCategory: str = None) -> None:
        self.category = category
        self.subCategory = subCategory or None


def validateParam(paramName: str, val: str):
    """Validate a segment of a static component custom_id

    :param paramName: The name of the custom_id segment
    :type paramName: str
    :param val: The value to validate
    :type val: str
    :raises ValueError: If `val` is not a valid value for a static component custom_id segment
    """
    if cfg.staticComponentCustomIdSeparator in val:
        raise ValueError(f"Invalid {paramName} '{val}' - cannot contain reserved character '{cfg.staticComponentCustomIdSeparator}'")


def validateCustomId(customId: str):
    """Validate a static component custom_id

    :param customId: The custom_id to validate
    :type customId: str
    :raises ValueError: If `customId` is not a valid custom_id
    """
    if len(customId) > 100:
        raise ValueError(f"Resulting custom_id is too long. The combined length of category, subCategory and args must be less than {100 - len(cfg.staticComponentCustomIdPrefix) - 2 * len(cfg.staticComponentCustomIdSeparator)} characters")


def staticComponentCallback(
    *,
    category: str = "",
    subCategory: str = ""
):
    """Decorator marking a coroutine as a static component callback.
    The callback for static components identifying this callback by category/subcategory will be preserved across bot restarts

    Example usage:
    ```
    class MyCog(BasedCog):
        @staticComponentCallback(category="myCallback")
        async def myCallback(interaction: Interaction, args: str):
            await interaction.response.send_message(f"This static callback received args: {args}")

        @app_commands.command(name="send-static-menu")
        async def sendStaticMenu(interaction: Interaction):
            staticButton = Button(label="send callback")
            staticButton = staticComponent(staticButton, category="myCallback", args="hello")
            view.add_item(staticButton)
            await interaction.response.send_message(view=view)
    ```
    If the `send-static-menu` app command is sent, then a message will be sent in return with a button to trigger `myCallback`.
    Clicking this button will send another message with the content "hello".
    If the bot is restarted, then the button will still work.
    This works by attaching a known `custom_id` to the button, containing the static component category/sub-category and args.

    :var category: The category of the static component
    :type category: str
    :var subCategory: The sub-category of the static component
    :type subCategory: Optional[str]
    """
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
    """Get the static component metadata attached to a static component callback
    I.e the category/sub-category

    :param callback: The callback
    :type callback: basedApp.CallBackType
    :raises TypeError: If `callback` is not registered as a static component callback
    :return: The static component metadata attached to `callback`
    :rtype: StaticComponentCallbackMeta
    """
    if basedApp.appType(callback) != basedApp.BasedAppType.StaticComponent:
        raise TypeError("The callback is not a static component callback")
    return StaticComponentCallbackMeta(*callback.__static_component_meta__)


def staticComponentCustomId(category: str, subCategory: str = "", args: str = "") -> str:
    """Construct a `custom_id` to represent an instance of a static component

    :param category: The category of the static component callback
    :type category: str
    :param subCategory: The sub-category of the static component callback
    :type subCategory: str, optional
    :param args: Arguments for this instance of the static component to pass to the callback (default "")
    :type args: str, optional
    :return: A `custom_id` that, when attached to an interacted-with component (e.g a button), will call the identified static component callback
    :rtype: str
    """
    validateParam("category", category)
    validateParam("subCategory", subCategory)
    validateParam("args", args)
    customId = cfg.staticComponentCustomIdPrefix + category + cfg.staticComponentCustomIdSeparator + (subCategory or "")
    if args:
        customId += cfg.staticComponentCustomIdSeparator + args
    validateCustomId(customId)
    return customId


inComponent = TypeVar("inComponent", bound=Component)


def staticComponent(component: inComponent, category: str, subCategory: str = "", args: str = "") -> inComponent:
    """Instruct a discord Component to call a static component callback, by assigning it a `custom_id`.

    :param category: The category of the static component callback
    :type category: str
    :param subCategory: The sub-category of the static component callback
    :type subCategory: str, optional
    :param args: Arguments for this instance of the static component to pass to the callback (default "")
    :type args: str, optional
    :return: `component`
    :rtype: str
    """
    if not hasattr(component, "custom_id"):
        raise ValueError(f"component type {type(component).__name__} cannot be static. Must have a custom_id")
    component.custom_id = staticComponentCustomId(category, subCategory, args)
    return component


def staticComponentKey(category: str, subCategory: str = "") -> str:
    """Construct a key under which a static component callback should be registered on the client
    The key should uniquely identify a static component callback

    :var category: The category of the static component
    :type category: str
    :var subCategory: The sub-category of the static component
    :type subCategory: Optional[str]
    :return: A key which uniquely identifies a static component callback
    :rtype: str
    """
    key = cfg.staticComponentCustomIdPrefix + category + cfg.staticComponentCustomIdSeparator + (subCategory or "")
    validateCustomId(key)
    return key


def customIdIsStaticComponent(customId: str) -> bool:
    """Decide whether a component `custom_id` could represent a static component

    :param customId: The `custom_id`
    :type customId: str
    :return: `True` if `customid` might represent a static component, `False` if it definitely does not
    :rtype: bool
    """
    return customId.startswith(cfg.staticComponentCustomIdPrefix)


def staticComponentMeta(customId: str) -> StaticComponentMeta:
    """Unpack a static component `custom_id` into metadata: category, subcategory and args

    :param customId: The `custom_id` to unpack
    :type customId: str
    :raises ValueError: If `customId` does not represent a static component
    :return: metadata about the instance of the static component
    :rtype: StaticComponentMeta
    """
    if not customIdIsStaticComponent(customId):
        raise ValueError("customId does not represent a static component")
    rest = customId[len(cfg.staticComponentCustomIdPrefix):]
    split = rest.split(cfg.staticComponentCustomIdSeparator)
    return StaticComponentMeta(*split)


async def maybeDefer(interaction: Interaction, ephemeral: bool = False, thinking: bool = False):
    """Defer an interaction response, unless it has already been responded to.

    :param interaction: The interaction
    :type interaction: Interaction
    :param ephemeral: Whether the deferral message should be ephemeral, defaults to False
    :type ephemeral: bool, optional
    :param thinking: Whether the deferral message should show the 'thinking' message, defaults to False
    :type thinking: bool, optional
    """
    if not interaction.response._responded:
        await interaction.response.defer(ephemeral=ephemeral, thinking=thinking)


async def editWithFallback(interaction: Interaction, msg: Message, *args, **kwargs):
    """If the interaction has been responded to, edit `msg`. Otherwise, edit the original message of the interaction.
    `*args` and `*kwargs` are passed to the message edit method.

    :param interaction: The interaction
    :type interaction: Interaction
    :param msg: A message to fallback onto editing, if `interaction` has been reseponded to
    :type msg: Message
    """
    if interaction.response._responded:
        await msg.edit(*args, **kwargs)
    else:
        await interaction.edit_original_message(*args, **kwargs)


class Menu:
    """Represents a menu page, with an embed and view.

    :var embed: The embed content of the menu
    :type embed: Embed
    :var view: The interactable content of the menu
    :type view: View
    """
    def __init__(self, view: View, embed: Embed):
        self.view = view
        self.embed = embed


def callbackWithChecks(callback: Union[Callable[[Interaction], bool], Callable[[Interaction], Awaitable[bool]]], *checks: Union[Callable[[Interaction], bool], Callable[[Interaction], Awaitable[bool]]]) -> Callable[[Interaction], Awaitable]:
    """Construct a callback that performs all of the checks in `checks` and, if they were all successful, calls `callback`.
    All of `callback` and `checks` may be synchronous or asynchronous.

    :param callback: The callback to call if all checks pass
    :type callback: Union[Callable[[Interaction], bool], Callable[[Interaction], Awaitable[bool]]]
    :return: A callback that, when triggered, will perform all checks and then call `callback` if the checks pass
    :rtype: Callable[[Interaction], Awaitable]
    """
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
    """UNDER CONSTRUCTION
    """
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
