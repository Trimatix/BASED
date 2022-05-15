from discord import app_commands
from discord.utils import MISSING
from typing import Dict, Type, Union
from .accessLevel import _AccessLevelBase, AccessLevel, accessLevelNamed, defaultAccessLevel
from .commandChecks import requireAccess
from .basedApp import basedApp, BasedAppType, _ensureAppType, CallBackType


class BasedCommandMeta:
    def __init__(self, accessLevel: _AccessLevelBase = MISSING, showInHelp: bool = True, helpSection: str = None, formattedDesc: str = None, formattedParamDescs : Dict[str, str] = None):
        self.accessLevel = accessLevel
        self.showInHelp = showInHelp
        self.helpSection = helpSection
        self.formattedDesc = formattedDesc
        self.formattedParamDescs = formattedParamDescs


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

        basedApp(func.callback, BasedAppType.AppCommand)
        setattr(func.callback, "__based_command_meta__", BasedCommandMeta(accessLevel, showInHelp, helpSection, formattedDesc, formattedParamDescs))

        if accessLevel is not MISSING:
            func.add_check(requireAccess(accessLevel))

        return func

    return decorator


def commandMeta(command: app_commands.Command) -> BasedCommandMeta:
    if hasattr(command.callback, "__based_command_meta__"):
        return command.callback.__based_command_meta__
    return BasedCommandMeta()


def accessLevel(command: app_commands.Command) -> _AccessLevelBase:
    level = commandMeta(command).accessLevel
    return level if level is not MISSING else defaultAccessLevel()
