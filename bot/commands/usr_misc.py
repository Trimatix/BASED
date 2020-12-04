import discord

from . import commandsDB as bbCommands
from . import util_help
from .. import lib


async def cmd_help(message : discord.Message, args : str, isDM : bool):
    """Print the help strings defined in bbData as an embed.
    If a command is provided in args, the associated help string for just that command is printed.

    :param discord.Message message: the discord message calling the command
    :param str args: empty, or a single command name
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    await util_help.util_autohelp(message, args, isDM, 0)

bbCommands.register("help", cmd_help, 0, allowDM=True, signatureStr="**help** *[page number, section or command]*",
    shortHelp="Show usage information for available commands.\nGive a specific command for detailed info about it, or give a page number or give a section name for brief info.",
    longHelp="Show usage information for available commands.\nGive a specific command for detailed info about it, or give a page number or give a section name for brief info about a set of commands. These are the currently valid section names:\n- Bounties\n- Economy\n- GOF2 Info\n- Home Servers\n- Loadout\n- Miscellaneous",
    useDoc=False)


async def cmd_source(message : discord.Message, args : str, isDM : bool):
    """Print a short message with information about BountyBot's source code.

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    srcEmbed = lib.discordUtil.makeEmbed(authorName="BB Source Code", desc="I am written using the rewrite branch of discord's python API.\n",
                         col=discord.Colour.purple(), footerTxt="BountyBot Source", icon="https://image.flaticon.com/icons/png/512/25/25231.png")
    srcEmbed.add_field(name="__GitHub Repository__",
                       value="My source code is public, and open to community contribution.\n[Click here](https://github.com/Trimatix/GOF2BountyBot/) to view my GitHub repo - please note, the project's readme file has not been written yet!", inline=False)
    srcEmbed.add_field(name="__Upcoming Features__",
                       value="To see a list of upcoming goodies, take a look at the [todo list](https://github.com/Trimatix/GOF2BountyBot/projects/1).\nIf you would like to make a feature request or suggestion, please ping or DM `Trimatix#2244`.\nIf you would like to help contribute to BountyBot, the todo list is a solid place to start!", inline=False)
    srcEmbed.add_field(name="__Special Thanks__", value=" • **DeepSilver FishLabs**, for building the fantastic game franchise that this bot is dedicated to. I don't own any Galaxy on Fire assets intellectual property, nor rights to any assets the bot references.\n • **The BountyBot testing team** who have all been lovely and supportive since the beginning, and who will *always* find a way to break things ;)\n • **NovahKiin22**, for his upcoming major feature release, along with minor bug fixes and *brilliant* insight throughout development\n • **Poisonwasp**, for another minor bug fix, but mostly for his continuous support\n • **You!** The community is what makes developing this bot so fun :)", inline=False)
    await message.channel.send(embed=srcEmbed)

bbCommands.register("source", cmd_source, 0, allowDM=True, signatureStr="**source**", shortHelp="Show links to the project's GitHub page and todo list, and some information about the people behind BountyBot.")
