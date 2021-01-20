from types import FunctionType
from typing import List
from discord import Message
from ..lib.exceptions import IncorrectCommandCallContext


class CommandRegistry:
    """Represents a registration of a command in a HeirarchicalCommandsDB.

    :var ident: The string command name by which this command is identified and called
    :vartype ident: str
    :var func: A reference to the function to call upon calling this CommandRegistry
    :vartype func: FunctionType
    :var forceKeepArgsCasing: Whether to pass arguments to the function with their original casing.
                                If False, arguments will be transformed to lower case before passing.
    :vartype forceKeepArgsCasing: bool
    :var forceKeepCommandCasing: Whether the command must be called with exactly the correct casing
    :vartype forceKeepCommandCasing: bool
    :var allowDM: Allow calling of this command from DMs.
    :vartype allowDM: bool
    :var signatureStr: A short string naming each parameter in the command signature
    :vartype signatureStr: str
    :var shortHelp: A short string describing the command
    :vartype shortHelp: str
    :var longHelp: A longer help string describing in full parameters and command usage
    :vartype longHelp: str
    """

    def __init__(self, ident: str, func: FunctionType, forceKeepArgsCasing: bool, forceKeepCommandCasing: bool,
                    allowDM: bool, allowHelp: bool, aliases: List[str] = None, signatureStr: str = "", shortHelp: str = "",
                    longHelp: str = "", helpSection: str = "miscellaneous"):
        """
        :param str ident: The string command name by which this command is identified and called
        :param FunctionType func: A reference to the function to call upon calling this CommandRegistry
        :param bool forceKeepArgsCasing: Whether to pass arguments to the function with their original casing.
                                        If False, arguments will be transformed to lower case before passing.
        :param bool forceKeepCommandCasing: Whether the command must be called with exactly the correct casing
        :param bool allowDM: Allow calling of this command from DMs
        :param bool allowHelp: If False, do not display this command in help listings.
        :param List[str] aliases: List of alternative names for this command (Default [])
        :param str signatureStr: A short string naming each parameter in the command signature (Default "")
        :param str shortHelp: A short string describing the command (Default "")
        :param str longHelp: A longer help string describing in full parameters and command usage (Default "")
        :param str helpSection: The name of the help section containing this command (Default "miscellaneous")
        """
        self.ident = ident
        self.func = func
        self.forceKeepArgsCasing = forceKeepArgsCasing
        self.forceKeepCommandCasing = forceKeepCommandCasing
        self.allowDM = allowDM
        self.allowHelp = allowHelp
        self.aliases = aliases if aliases is not None else []
        self.signatureStr = signatureStr
        self.shortHelp = shortHelp
        self.longHelp = longHelp
        self.helpSection = helpSection


    async def call(self, message: Message, args: str, isDM: bool):
        """Call this command.

        :param discord.message message: the discord message calling the command.
                                        This is required for referencing the author and sending responses
        :param str args: string containing arguments to pass to the command
        :param bool isDM: Whether the command was called from DMs or not
        :raise IncorrectCommandCallContext: When attempting to call a non-DMable command from DMs
        """
        if isDM and not self.allowDM:
            raise IncorrectCommandCallContext("Attempted to call command '" + self.ident +
                                              "' from DMs, but command is not allowed in DMs.")
        await self.func(message, args if self.forceKeepArgsCasing else args.lower(), isDM)
