from enum import Enum
from typing import Any, Awaitable, Callable, Coroutine, Dict, Iterable, List, Optional, Tuple, Type

from discord.ext.commands.cog import Cog
from discord import app_commands, Interaction, Component

from . import basedCommand, basedComponent
from .. import client

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
    return hasattr(callback, "__cog_name__") and callback.__cog_name__ is not None


def setCogApp(callback: Callable, cog: Type["BasedCog"]):
    """Mark a BASED app as belonging to a cog

    :param callback: The callback
    :type callback: Callable
    :param cog: The cog type to mark the callback as belonging to
    :type cog: Type[&quot;BasedCog&quot;]
    """
    setattr(callback, "__cog_name__", cog.__name__)


def setNotCogApp(callback: Callable):
    """Remove a BASED app's assignment to a cog

    :param callback: The callback
    :type callback: Callable
    """
    setattr(callback, "__cog_name__", None)


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
    return callback.__cog_name__


class BasedCog(Cog):
    """An extension of `Cog` to allow for housing of BASED apps.
    This current includes BASED commands and static component callbacks.

    :var basedCommands: All BASED commands defined within the cog
    :type basedCommands: Dict[app_commands.Command, "basedCommand.BasedCommandMeta"]
    :var basedCommands: All static component callbacks defined within the cog
    :type basedCommands: Dict[Tuple[str, str], CallBackType]
    """
    basedCommands: Dict[app_commands.Command, "basedCommand.BasedCommandMeta"] = {}
    staticComponentCallbacks: Dict[Tuple[str, str], CallBackType] = {}

    def _inject(self, bot: "client.BasedClient", override: bool, guild, guilds) -> Coroutine:
        """Registers all BASED apps in the cog with the provided client, and then passes cog injection responsibility up
        to the discord Cog base class
        """
        # __cog_app_commands__ is assigned in discord._CogMeta.__new__, which does not make new copies of commands
        for command in self.__cog_app_commands__:
            if appType(command.callback) == BasedAppType.AppCommand:
                self.basedCommands[command] = basedCommand.commandMeta(command)
                setCogApp(command.callback, type(self))
                bot.addBasedCommand(command)


        for method in type(self).__dict__.values():
            if appType(method) == BasedAppType.StaticComponent:
                meta = basedComponent.staticComponentCallbackMeta(method)
                key = basedComponent.staticComponentKey(meta.category, meta.subCategory)
                self.staticComponentCallbacks[key] = method
                setCogApp(method, type(self))
                bot.addStaticComponent(method)

        return super()._inject(bot=bot, override=override, guild=guild, guilds=guilds)


    def _eject(self, bot: "client.BasedClient", guild_ids: Optional[Iterable[int]]) -> Coroutine[Any, Any, None]:
        """Un-registers all BASED apps in the cog from the provided client, and then passes cog ejection responsibility up
        to the discord Cog base class
        """
        for command in self.basedCommands:
            bot.basedCommands.pop(command, None)

        for key in self.staticComponentCallbacks:
            bot.staticComponentCallbacks.pop(key, None)

        return super()._eject(bot, guild_ids)
