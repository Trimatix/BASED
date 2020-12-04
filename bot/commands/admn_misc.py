import discord

from . import commandsDB as bbCommands
from . import util_help
from .. import botState


async def admin_cmd_admin_help(message : discord.Message, args : str, isDM : bool):
    """admin command printing help strings for admin commands as defined in bbData

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    await util_help.util_autohelp(message, args, isDM, 2)

bbCommands.register("admin-help", admin_cmd_admin_help, 2, signatureStr="**admin-help** *[page number, section or command]*",
                                                            shortHelp="Display information about admin-only commands.\nGive a specific command for detailed info about it, or give a page number or give a section name for brief info.",
                                                            longHelp="Display information about admin-only commands.\nGive a specific command for detailed info about it, or give a page number or give a section name for brief info about a set of commands. These are the currently valid section names:\n- Miscellaneous")


async def admin_cmd_set_prefix(message : discord.Message, args : str, isDM : bool):
    """admin command setting the calling guild's command prefix

    :param discord.Message message: the discord message calling the command
    :param str args: the command prefix to use
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    callingBGuild = botState.guildsDB.getGuild(message.guild.id)

    if not args:
        await message.channel.send("Please provide the command prefix you would like to set. E.g: `" + callingBGuild.commandPrefix + "set-prefix $`")
    else:
        callingBGuild.commandPrefix = args
        await message.channel.send("Command prefix set.")

bbCommands.register("set-prefix", admin_cmd_set_prefix, 2, signatureStr="**set-prefix <prefix>**",
                                                            shortHelp="Set the prefix you would like to use for bot commands in this server.")

