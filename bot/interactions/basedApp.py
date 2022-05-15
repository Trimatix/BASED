from enum import Enum
from typing import Any, Awaitable, Callable, Coroutine, Dict, Iterable, List, Optional, Tuple, Type

from discord.ext.commands.cog import Cog
from discord import app_commands, Interaction, Component

from . import basedCommand, basedComponent
from .. import client

class BasedAppType(Enum):
    none = 0
    AppCommand = 1
    StaticComponent = 2

CallBackType = Callable[[Interaction], Awaitable]


def appType(callback: CallBackType) -> BasedAppType:
    try:
        return callback.__based_app_type__
    except AttributeError:
        return BasedAppType.none


def _ensureAppType(callback: CallBackType, basedAppType: BasedAppType):
    callbackType = appType(callback)
    if callbackType not in (basedAppType, BasedAppType.none):
        raise ValueError(f"callback {callback.__name__} is already based app type {callbackType}")


def basedApp(callback: CallBackType, basedAppType: BasedAppType) -> CallBackType:
    _ensureAppType(callback, basedAppType)
    setattr(callback, "__based_app_type__", basedAppType)


def isBasedApp(callback: Callable) -> bool:
    return appType(callback) != BasedAppType.none


def isCogApp(callback: Callable) -> bool:
    return hasattr(callback, "__cog_name__") and callback.__cog_name__ is not None


def setCogApp(callback: Callable, cog: Type["BasedCog"]):
    setattr(callback, "__cog_name__", cog.__name__)


def setNotCogApp(callback: Callable):
    setattr(callback, "__cog_name__", None)


def getCogAppCogName(callback: Callable) -> str:
    if not isCogApp(callback):
        raise ValueError(f"The callback {callback.__name__} is not a cog app")
    return callback.__cog_name__


class BasedCog(Cog):
    basedCommands: Dict[app_commands.Command, "basedCommand.BasedCommandMeta"] = {}
    staticComponentCallbacks: Dict[Tuple[str, str], CallBackType] = {}

    def _inject(self, bot: "client.BasedClient", override: bool, guild, guilds) -> Coroutine:
        # __cog_app_commands__ is assigned in discord._CogMeta.__new__, which does not make new copies of commands
        for command in self.__cog_app_commands__:
            if appType(command.callback) == BasedAppType.AppCommand:
                self.basedCommands[command] = basedCommand.commandMeta(command)
                setCogApp(command.callback, type(self))


        for method in type(self).__dict__.values():
            if appType(method) == BasedAppType.StaticComponent:
                meta = basedComponent.staticComponentCallbackMeta(method)
                key = basedComponent.staticComponentKey(meta.category, meta.subCategory)
                self.staticComponentCallbacks[key] = method
                setCogApp(method, type(self))

        bot.basedCommands.update(self.basedCommands)
        bot.staticComponentCallbacks.update(self.staticComponentCallbacks)

        return super()._inject(bot=bot, override=override, guild=guild, guilds=guilds)


    def _eject(self, bot: "client.BasedClient", guild_ids: Optional[Iterable[int]]) -> Coroutine[Any, Any, None]:
        for command in self.basedCommands:
            bot.basedCommands.pop(command, None)

        for key in self.staticComponentCallbacks:
            bot.staticComponentCallbacks.pop(key, None)

        return super()._eject(bot, guild_ids)
