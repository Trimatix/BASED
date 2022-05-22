from discord import app_commands
from discord.utils import MISSING
from typing import Dict, Optional, Type, Union
from .accessLevels import _AccessLevelBase, AccessLevel, accessLevelNamed, defaultAccessLevel
from .commandChecks import requireAccess
from .basedApp import basedApp, BasedAppType
from . import basedComponent
from ..cfg import cfg
from .. import lib


class BasedCommandMeta:
    """A data class defining attributes of a BASED command.

    :var accessLevel: The access level required to use the command
    :type accessLevel: _AccessLevelBase
    :var showInHelp: Whether or not this command should appear in help command listings
    :type showInHelp: bool
    :var helpSection: The section of the help command in which to list this command
    :type helpSection: Optional[str]
    :var formattedDesc: A description of the command with more allowed length and markdown formatting, to be used in help commands
    :type formattedDesc: Optional[str]
    :var formattedParamDescs: Descriptions for each parameter of the command with more allowed length and markdown formatting, to be used in help commands
    :type formattedParamDescs: Optional[Dict[str, str]]
    """
    def __init__(self, accessLevel: _AccessLevelBase = MISSING, showInHelp: bool = True, helpSection: Optional[str] = None, formattedDesc: Optional[str] = None, formattedParamDescs : Optional[Dict[str, str]] = None):
        self._accessLevel = accessLevel
        self.showInHelp = showInHelp
        self._helpSection = helpSection
        self.formattedDesc = formattedDesc
        self.formattedParamDescs = formattedParamDescs

    
    @property
    def accessLevel(self):
        """The access level required to use the command

        :return: The access level required to use the command
        :rtype: _AccessLevelBase
        """
        return self._accessLevel if self._accessLevel is not MISSING else defaultAccessLevel()


    @property
    def helpSection(self):
        """The help section in which to list this command

        :return: The help section in which to list this command
        :rtype: str
        """
        return self._helpSection or cfg.defaultHelpSection


def validateHelpSection(helpSection: str):
    """
    A help command static component consists of:
    - |help||
    - section
      #
    - page number (2 chars)
      #
    - access level (2 chars)
      #
    - show all sections (1 char)
    """
    #max customId len    prefix                     help   customId separators                                          # page access showAll
    maxLength = 100 - len(cfg.defaultCommandPrefix) - 4 - len(basedComponent.STATIC_COMPONENT_CUSTOM_ID_SEPARATOR) * 2 - 3 - 2 - 2 - 1
    if len(helpSection) > maxLength:
        raise ValueError(f"Help section too long, must be less than {maxLength} characters")
    if "#" in helpSection:
        raise ValueError(f"Invalid helpSection '{helpSection}' - cannot contain reserved character '#'")
    basedComponent.validateParam("helpSection", helpSection)


def basedCommand(
    *,
    accessLevel: Union[Type[AccessLevel], str] = MISSING,
    showInHelp: bool = True,
    helpSection: str = None,
    formattedDesc: str = None,
    formattedParamDescs : Dict[str, str] = None
):
    """Decorator that marks a discord app command as a BASED command.

    :param accessLevel: The access level required to use the command. A check will be added for this.
    :type accessLevel: Union[Type[AccessLevel], str], optional
    :param showInHelp: Whether or not to show the command in help listings, defaults to True
    :type showInHelp: bool, optional
    :param helpSection: The section of the help command in which to list this command, defaults to None
    :type helpSection: str, optional
    :param formattedDesc: A description of the command with more allowed length and markdown formatting, to be used in help commands, defaults to None
    :type formattedDesc: str, optional
    :param formattedParamDescs: Descriptions for each parameter of the command with more allowed length and markdown formatting, to be used in help commands, defaults to None
    :type formattedParamDescs: Dict[str, str], optional
    """
    def decorator(func, accessLevel=accessLevel, showInHelp=showInHelp, helpSection=helpSection, formattedDesc=formattedDesc, formattedParamDescs=formattedParamDescs):
        if not isinstance(func, app_commands.Command):
            raise TypeError("decorator can only be applied to app commands")

        if isinstance(accessLevel, str):
            accessLevel = accessLevelNamed(accessLevel)

        if helpSection is not None:
            validateHelpSection(helpSection)

        basedApp(func.callback, BasedAppType.AppCommand)
        setattr(func.callback, "__based_command_meta__", BasedCommandMeta(accessLevel, showInHelp, helpSection, formattedDesc, formattedParamDescs))

        if accessLevel is not MISSING:
            func.add_check(requireAccess(accessLevel))

        return func

    return decorator


def commandMeta(command: app_commands.Command) -> BasedCommandMeta:
    """Get the metadata stored against a BASED command
    If the command is not a BASED command, then the default metadata is returned

    :param command: The command
    :type command: app_commands.Command
    :return: The metadata stored against the command
    :rtype: BasedCommandMeta
    """
    if hasattr(command.callback, "__based_command_meta__"):
        return command.callback.__based_command_meta__
    return BasedCommandMeta()


def accessLevel(command: app_commands.Command) -> _AccessLevelBase:
    """Get the access level required to use a BASED command
    If the command is not a BASED command, then the default access level is returned

    :param command: The command
    :type command: app_commands.Command
    :return: The access level required to use the command
    :rtype: _AccessLevelBase
    """
    return commandMeta(command).accessLevel
