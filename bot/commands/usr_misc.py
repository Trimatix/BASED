from bot import botState
from bot.cfg import versionInfo
import discord
from datetime import datetime
import operator

from . import commandsDB as botCommands
from . import util_help
from .. import lib
from ..cfg import versionInfo, cfg


TROPHY_ICON = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/248/trophy_1f3c6.png"


async def cmd_help(message: discord.Message, args: str, isDM: bool):
    """Print the help strings as an embed.
    If a command is provided in args, the associated help string for just that command is printed.

    :param discord.Message message: the discord message calling the command
    :param str args: empty, or a single command name
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    await util_help.util_autohelp(message, args, isDM, 0)

botCommands.register("help", cmd_help, 0, allowDM=True, signatureStr="**help** *[page number, section or command]*",
                     shortHelp="Show usage information for available commands.\nGive a specific command for detailed info " +
                                "about it, or give a page number or give a section name for brief info.",
                     longHelp="Show usage information for available commands.\nGive a specific command for detailed info " +
                                "about it, or give a page number or give a section name for brief info about a set of " +
                                "commands. These are the currently valid section names:\n- Miscellaneous",
                     useDoc=False)


async def cmd_source(message: discord.Message, args: str, isDM: bool):
    """Print a short message with information about the bot's source code.

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    srcEmbed = lib.discordUtil.makeEmbed(authorName="Source Code",
                                         col=discord.Colour.purple(),
                                         icon="https://image.flaticon.com/icons/png/512/25/25231.png",
                                         footerTxt="Bot Source",
                                         footerIcon="https://i.imgur.com/7SMgF0t.png")
    srcEmbed.add_field(name="Uptime",
                       value=lib.timeUtil.td_format_noYM(datetime.utcnow() - botState.client.launchTime))
    srcEmbed.add_field(name="Author",
                       value="Trimatix#2244 & sHiiNe#4265")
    srcEmbed.add_field(name="API",
                       value="[Discord.py " + discord.__version__ + "](https://github.com/Rapptz/discord.py/)")
    srcEmbed.add_field(name="BASED",
                       value="[BASED " + versionInfo.BASED_VERSION + "](https://github.com/Trimatix/BASED)")
    srcEmbed.add_field(name="GitHub",
                       value="[Trimatix-indie/SuperDeckBreaker](https://github.com/Trimatix-indie/SuperDeckBreaker)")
    srcEmbed.add_field(name="Invite",
                       value="No public invite currently.")
    await message.channel.send(embed=srcEmbed)

botCommands.register("source", cmd_source, 0, allowDM=True, signatureStr="**source**",
                     shortHelp="Show links to the project's GitHub page.")


async def cmd_leaderboard(message : discord.Message, args : str, isDM : bool):
    """display leaderboards for different statistics
    if no arguments are given, display the local leaderboard for rounds won.
    if `global` is given, display the appropriate leaderbaord across all guilds
    if `wins` is given, display the leaderboard for game wins

    :param discord.Message message: the discord message calling the command
    :param str args: string containing the arguments the user passed to the command
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # across all guilds?
    globalBoard = False
    # stat to display
    stat = "round wins"
    # "global" or the local guild name
    boardScope = message.guild.name
    # user friendly string for the stat
    boardTitle = "Rounds Won"
    # units for the stat
    boardUnit = "Round"
    boardUnits = "Rounds"
    boardDesc = "*Total number of rounds won"

    if isDM:
        prefix = cfg.defaultCommandPrefix
    else:
        prefix = botState.guildsDB.getGuild(message.guild.id).commandPrefix

    # change leaderboard arguments based on the what is provided in args
    if args != "":
        argsSplit = args.split(" ")
        
        if len(argsSplit) > 3:
            await message.channel.send(":x: Too many arguments! Please only specify one leaderboard. E.g: `" + prefix \
                                        + "leaderboard global wins`")
            return
        for arg in argsSplit:
            if arg not in ["wins", "round wins", "global"]:
                await message.channel.send(":x: Unknown argument: '**" + arg + "**'. Please refer to `" + prefix \
                                            + "help leaderboard`")
                return
        if "wins" in argsSplit:
            stat = "game wins"
            boardTitle = "Games Won"
            boardUnit = "Game"
            boardUnits = "Games"
            boardDesc = "*Total number of games won"
        if "global" in argsSplit:
            globalBoard = True
            boardScope = "Global Leaderboard"
            boardDesc += " across all servers"

    boardDesc += ".*"

    # get the requested stats and sort users by the stat
    inputDict = {}
    for user in botState.usersDB.getUsers():
        if (globalBoard and botState.client.get_user(user.id) is not None) or \
                (not globalBoard and message.guild.get_member(user.id) is not None):
            inputDict[user.id] = user.getStatByName(stat)
    sortedUsers = sorted(inputDict.items(), key=operator.itemgetter(1))[::-1]

    # build the leaderboard embed
    leaderboardEmbed = lib.discordUtil.makeEmbed(titleTxt=boardTitle, authorName=boardScope,
                                                    icon=TROPHY_ICON, col=discord.Colour.random(), desc=boardDesc)

    # add all users to the leaderboard embed with places and values
    externalUser = False
    first = True
    for place in range(min(len(sortedUsers), 10)):
        # handling for global leaderboards and users not in the local guild
        if globalBoard and message.guild.get_member(sortedUsers[place][0]) is None:
            leaderboardEmbed.add_field(value="*" + str(place + 1) + ". " \
                                            + str(botState.client.get_user(sortedUsers[place][0])),
                                        name=("⭐ " if first else "") + str(sortedUsers[place][1]) + " " \
                                            + (boardUnit if sortedUsers[place][1] == 1 else boardUnits), inline=False)
            externalUser = True
            if first:
                first = False
        else:
            leaderboardEmbed.add_field(value=str(place + 1) + ". " + message.guild.get_member(sortedUsers[place][0]).mention,
                                        name=("⭐ " if first else "") + str(sortedUsers[place][1]) + " " \
                                            + (boardUnit if sortedUsers[place][1] == 1 else boardUnits), inline=False)
            if first:
                first = False
    # If at least one external use is on the leaderboard, give a key
    if externalUser:
        leaderboardEmbed.set_footer(
            text="An `*` indicates a user that is from another server.")
    # send the embed
    await message.channel.send(embed=leaderboardEmbed)

botCommands.register("leaderboard", cmd_leaderboard, 0, allowDM=False, signatureStr="**leaderboard** *[global] [wins]*",
                        longHelp="Show the leaderboard for total number of rounds won. Give `global` for the global leaderboard, " \
                            + "not just this server.\n> Give `wins` for the total *game* wins leaderboard.")
