from enum import Enum
from inspect import iscoroutinefunction
from typing import Any, Awaitable, Callable, Coroutine, Dict, Iterable, List, Optional, Tuple, Type

from discord.ext.commands.cog import Cog
from discord import app_commands, Interaction, Component

from . import basedCommand, basedComponent
from .. import client

class DelayedPropogationFlag: pass

COG_INSTANCE = DelayedPropogationFlag()

class BasedAppType(Enum):
    """Identifies a callback as a particular type of BASED app.
    """
    none = 0
    AppCommand = 1
    StaticComponent = 2

CallBackType = Callable[[Interaction], Awaitable]


def appType(callback: CallBackType) -> BasedAppType:
    """Decide the BASED app type for a callback, if any

    :param callback: The callback to examine
    :type callback: CallBackType
    :return: The BASED app type for `callback`
    :rtype: BasedAppType
    """
    try:
        return callback.__based_app_type__
    except AttributeError:
        return BasedAppType.none


def _ensureAppType(callback: CallBackType, basedAppType: BasedAppType):
    """Raise an exception of `callback` is a BASED app type other than `basedAppType` or `none`.

    :param callback: The callback to examine
    :type callback: CallBackType
    :param basedAppType: The basedAppType to allow `callback` to be
    :type basedAppType: BasedAppType
    :raises ValueError: If `callback` is any BASED app type other than `basedAppType` or `none`
    """
    callbackType = appType(callback)
    if callbackType not in (basedAppType, BasedAppType.none):
        raise ValueError(f"callback {callback.__name__} is already based app type {callbackType}")


def basedApp(callback: CallBackType, basedAppType: BasedAppType):
    """Mark a callback as a BASED app. This does not add the behaviour of the BASED app, it only
    marks the callback as of that type.

    :param callback: The callback to mark
    :type callback: CallBackType
    :param basedAppType: The BASED app type to mark `callback` as
    :type basedAppType: BasedAppType
    """
    _ensureAppType(callback, basedAppType)
    setattr(callback, "__based_app_type__", basedAppType)


def isBasedApp(callback: Callable) -> bool:
    """Decide whether `callback` has been marked as a BASED app

    :param callback: The callback
    :type callback: Callable
    :return: `True` if `callback` is a BASED app, `False` otherwise
    :rtype: bool
    """
    return appType(callback) != BasedAppType.none


def isCogApp(callback: Callable) -> bool:
    """Decide whether `callback` is a BASED app created within a `BasedCog`.

    :param callback: The callback
    :type callback: Callable
    :return: `True` if `callback` is a BASED app created within a `BasedCog`, `False` otherwise
    :rtype: bool
    """
    return "__cog_name__" in callback.__dict__ and callback.__dict__["__cog_name__"] is not None


def setCogApp(callback: Callable, cog: Type["BasedCog"]):
    """Mark a BASED app as belonging to a cog

    :param callback: The callback
    :type callback: Callable
    :param cog: The cog type to mark the callback as belonging to
    :type cog: Type[&quot;BasedCog&quot;]
    """
    callback.__dict__["__cog_name__"] = cog.__name__
    # setattr(callback, "__cog_name__", cog.__name__)


def setNotCogApp(callback: Callable):
    """Remove a BASED app's assignment to a cog

    :param callback: The callback
    :type callback: Callable
    """
    callback.__dict__["__cog_name__"] = None
    # setattr(callback, "__cog_name__", None)


def getCogAppCogName(callback: Callable) -> str:
    """Get the name of the cog that a BASED app has been assigned to

    :param callback: The callback
    :type callback: Callable
    :raises ValueError: If `callback` is not a BASED app created within a `BasedCog`
    :return: The name of the cog that defined `callback`
    :rtype: str
    """
    if not isCogApp(callback):
        raise ValueError(f"The callback {callback.__name__} is not a cog app")
    # return callback.__cog_name__
    return callback.__dict__["__cog_name__"]


class BasedCog(Cog):
    """An extension of `Cog` to allow for housing of BASED apps.
    This current includes BASED commands and static component callbacks.

    :var basedCommands: All BASED commands defined within the cog
    :type basedCommands: Dict[app_commands.Command, basedCommand.BasedCommandMeta]
    :var staticComponentCallbacks: All static component callbacks defined within the cog, by ID
    :type staticComponentCallbacks: Dict[basedComponent.StaticComponents, basedComponent.StaticComponentCallbackMeta]
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._basedCommands: Dict[app_commands.Command, "basedCommand.BasedCommandMeta"] = None
        self._staticComponentCallbacks: Dict["basedComponent.StaticComponents", "basedComponent.StaticComponentCallbackMeta"] = None


    @property
    def basedCommands(self):
        if self._basedCommands is None:
            raise ValueError("basedCommands is only available after cog injection")
        return self._basedCommands


    @property
    def staticComponentCallbacks(self):
        if self._staticComponentCallbacks is None:
            raise ValueError("staticComponentCallbacks is only available after cog injection")
        return self._staticComponentCallbacks

    
    def _inject(self, bot: "client.BasedClient", override: bool, guild, guilds) -> Coroutine:
        """Registers all BASED apps in the cog with the provided client, and then passes cog injection responsibility up
        to the discord Cog base class
        """
        self._basedCommands = {}
        self._staticComponentCallbacks = {}
        # __cog_app_commands__ is assigned in discord._CogMeta.__new__, which does not make new copies of commands
        for command in self.__cog_app_commands__:
            if appType(command.callback) == BasedAppType.AppCommand:
                self.basedCommands[command] = basedCommand.commandMeta(command)
                setCogApp(command.callback, type(self))
                bot.addBasedCommand(command)
        
        for methodName in dir(self):
            method = getattr(self, methodName)
            if appType(method) == BasedAppType.StaticComponent:
                meta = basedComponent.staticComponentCallbackMeta(method)
                self.staticComponentCallbacks[meta.ID] = meta
                setCogApp(method, type(self))
                bot.addStaticComponent(meta.callback)

        return super()._inject(bot=bot, override=override, guild=guild, guilds=guilds)


    def _eject(self, bot: "client.BasedClient", guild_ids: Optional[Iterable[int]]) -> Coroutine[Any, Any, None]:
        """Un-registers all BASED apps in the cog from the provided client, and then passes cog ejection responsibility up
        to the discord Cog base class
        """
        for command in self.basedCommands:
            bot.removeBasedCommand(command)

        for meta in self.staticComponentCallbacks.values():
            bot.removeStaticComponent(meta.ID)
            
        self._basedCommands = None
        self._staticComponentCallbacks = None

        return super()._eject(bot, guild_ids)


    @classmethod
    def staticComponentCallback(cls, ID: "basedComponent.StaticComponents"):
        """Decorator marking a coroutine as a static component callback.
        The callback for static components identifying this callback by ID will be preserved across bot restarts

        Example usage:
        ```
        class MyCog(BasedCog):
            @BasedCog.staticComponentCallback(StaticComponents.myCallback)
            async def myCallback(self, interaction: Interaction, args: str):
                await interaction.response.send_message(f"This static callback received args: {args}")

            @app_commands.command(name="send-static-menu")
            async def sendStaticMenu(interaction: Interaction):
                staticButton = Button(label="send callback")
                staticButton = StaticComponents.myCallback(staticButton, args="hello")
                view.add_item(staticButton)
                await interaction.response.send_message(view=view)
        ```
        If the `send-static-menu` app command is sent, then a message will be sent in return with a button to trigger `myCallback`.
        Clicking this button will send another message with the content "hello".
        If the bot is restarted, then the button will still work.
        This works by attaching a known `custom_id` to the button, containing the static component ID and args.

        :var ID: The ID of the static component in the `StaticComponents` enum
        :type ID: StaticComponents
        """
        def decorator(func: "basedComponent.StaticComponentCallbackType", ID=ID):
            if not iscoroutinefunction(func):
                raise TypeError("Decorator can only be applied to coroutines")

            # This special variation on the staticComponentCallback decorator delays setting of the 'cbSelf' meta field
            #   until cog instantiation. This usually would be a bad idea, because every class instance would try to
            #   register their static components against the client, causing a conflict. This issue is not present
            #   with Cogs, because they are effectively singular, meaning that this delayed propogation will only
            #   occur once per class
            if hasattr(func, "__self__"):
                cbSelf = basedComponent.validateStaticComponentCallbackSelf(func)
            else:
                cbSelf = COG_INSTANCE

            basedApp(func, BasedAppType.StaticComponent)
            setattr(func, "__static_component_meta__", basedComponent.StaticComponentCallbackMeta(func, ID, cbSelf))

            return func

        return decorator
