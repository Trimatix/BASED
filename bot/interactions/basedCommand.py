from discord import app_commands
from discord.ext.commands.cog import Cog
from discord.app_commands import commands as _dpy
from discord.abc import Snowflake
from discord.utils import MISSING
import functools
from typing import Callable, Dict, Optional, List, Type, Union, TYPE_CHECKING
from .accessLevel import _AccessLevelBase, AccessLevel, accessLevelNamed, defaultAccessLevel
import inspect
from .commandChecks import requireAccess
from .. import client
if TYPE_CHECKING:
    from typing_extensions import Self


class BasedCommandMeta:
    def __init__(self, accessLevel: _AccessLevelBase = MISSING, showInHelp: bool = True, helpSection: str = None, formattedDesc: str = None, formattedParamDescs : Dict[str, str] = None):
        self.accessLevel = accessLevel
        self.showInHelp = showInHelp
        self.helpSection = helpSection
        self.formattedDesc = formattedDesc
        self.formattedParamDescs = formattedParamDescs


class BasedCog(Cog):
    __basedCommandMeta__: Dict[app_commands.Command, BasedCommandMeta] = {}

    def _inject(self, bot: "client.BasedClient", override: bool, guild: Optional[Snowflake], guilds: List[Snowflake]) -> "Self":
        # __cog_app_commands__ is assigned in discord._CogMeta.__new__, which does not make new copies of commands
        for command in self.__cog_app_commands__:
            try:
                self.__basedCommandMeta__[command] = command.callback.__basedCommandMeta__
            except AttributeError:
                pass

        bot.__basedCommandMeta__.update(self.__basedCommandMeta__)

        return super()._inject(bot=bot, override=override, guild=guild, guilds=guilds)


def command(
    *,
    accessLevel: Union[Type[AccessLevel], str] = MISSING,
    showInHelp: bool = True,
    helpSection: str = None,
    formattedDesc: str = None,
    formattedParamDescs : Dict[str, str] = None
):
    def decorator(func, accessLevel=accessLevel, showInHelp=showInHelp, helpSection=helpSection, formattedDesc=formattedDesc, formattedParamDescs=formattedParamDescs):
        if not isinstance(func, app_commands.Command):
            raise TypeError("decorator can only be applied to app commands")

        if isinstance(accessLevel, str):
            accessLevel = accessLevelNamed(accessLevel)

        func.callback.__basedCommandMeta__ = BasedCommandMeta(accessLevel, showInHelp, helpSection, formattedDesc, formattedParamDescs)

        if accessLevel is not MISSING:
            func.add_check(requireAccess(accessLevel))

        return func

    return decorator


def commandMeta(command: app_commands.Command) -> BasedCommandMeta:
    if hasattr(command.callback, "__basedCommandMeta__"):
        return command.callback.__basedCommandMeta__
    return BasedCommandMeta()


def accessLevel(command: app_commands.Command) -> _AccessLevelBase:
    level = commandMeta(command).accessLevel
    return level if level is not MISSING else defaultAccessLevel()
