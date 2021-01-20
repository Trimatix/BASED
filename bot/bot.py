# Set up bot config

from .cfg import cfg, versionInfo


# Discord Imports

import discord
from discord.ext.commands import Bot as ClientBaseClass


# Util imports

from datetime import datetime
import os
import traceback
import asyncio
import signal
import aiohttp


# BASED Imports

from . import lib, botState, logging
from .databases import guildDB, reactionMenuDB, userDB
from .scheduling.timedTask import TimedTask
from .scheduling.timedTaskHeap import TimedTaskHeap


async def checkForUpdates():
    """Check if any new BASED versions are available, and print a message to console if one is found.
    """
    try:
        BASED_versionCheck = await versionInfo.checkForUpdates(botState.httpClient)
    except versionInfo.UpdatesCheckFailed:
        print("⚠ BASED updates check failed. Either the GitHub API is down, " +
                "or your BASED updates checker version is depracated: " + versionInfo.BASED_REPO_URL)
    else:
        if BASED_versionCheck.updatesChecked and not BASED_versionCheck.upToDate:
            print("⚠ New BASED update " + BASED_versionCheck.latestVersion + " now available! See " +
                  versionInfo.BASED_REPO_URL + " for instructions on how to update your BASED fork.")


async def initializeEmojis():
    """Converts all of the expected emoji config vars from UninitializedBasedEmoji to BasedEmoji.
    Throws errors if initialization of any emoji failed.
    """
    emojiVars = []
    emojiListVars = []

    # Gather attribute names of emoji config vars
    for varname in cfg.defaultEmojis.attrNames:
        varvalue = getattr(cfg.defaultEmojis, varname)

        # ensure single emoji vars are emojis
        if type(varvalue) == lib.emojis.UninitializedBasedEmoji:
            emojiVars.append(varname)
            continue

        # ensure list emoji vars only contain emojis
        elif type(varvalue) == list:
            onlyEmojis = True
            for item in varvalue:
                if type(item) != lib.emojis.UninitializedBasedEmoji:
                    onlyEmojis = False
                    break
            if onlyEmojis:
                emojiListVars.append(varname)
                continue

        # raise an error on unexpected types
        raise ValueError("Invalid config variable in cfg.defaultEmojis: " + 
                            "Emoji config variables must be either UninitializedBasedEmoji or List[UninitializedBasedEmoji]")

    # Initialize emoji vars
    for varname in emojiVars:
        setattr(cfg.defaultEmojis, varname, lib.emojis.BasedEmoji.fromUninitialized(getattr(cfg.defaultEmojis, varname)))

    # Initialize lists of emojis vars
    for varname in emojiListVars:
        working = []
        for item in getattr(cfg.defaultEmojis, varname):
            working.append(lib.emojis.BasedEmoji.fromUninitialized(item))

        setattr(cfg.defaultEmojis, varname, working)


def setHelpEmbedThumbnails():
    """Loads the bot application's profile picture into all help menu embeds as the embed thumbnail.
    If no profile picture is set for the application, the default profile picture is used instead.
    """
    for levelSection in botCommands.helpSectionEmbeds:
        for helpSection in levelSection.values():
            for embed in helpSection:
                embed.set_thumbnail(url=botState.client.user.avatar_url_as(size=64))


def inferUserPermissions(message: discord.Message) -> int:
    """Get the commands access level of the user that sent the given message.
    
    :return: message.author's access level, as an index of cfg.userAccessLevels
    :rtype: int
    """
    if message.author.id in cfg.developers:
        return 3
    elif message.author.permissions_in(message.channel).administrator:
        return 2
    else:
        return 0


class GracefulKiller:
    """Class tracking receipt of SIGINT and SIGTERM signals under linux.
    This is used during the main loop to put the bot to sleep when requested.

    :var kill_now: Whether or not a termination signal has been received
    :vartype kill_now: bool
    """

    def __init__(self):
        """Register signal handlers"""
        self.kill_now = False
        signal.signal(signal.SIGINT, self.exit_gracefully) # keyboard interrupt
        signal.signal(signal.SIGTERM, self.exit_gracefully) # graceful exit request

    def exit_gracefully(self, signum, frame):
        """Termination signal received, mark kill indicator"""
        self.kill_now = True


class BasedClient(ClientBaseClass):
    """A minor extension to discord.ext.commands.Bot to include database saving and extended shutdown procedures.

    A command_prefix is assigned to this bot, but no commands are registered to it, so this is effectively meaningless.
    I chose to assign a zero-width character, as this is unlikely to ever be chosen as the bot's actual command prefix,
    minimising erroneous commands.Bot command recognition. 

    :var bot_loggedIn: Tracks whether or not the bot is currently logged in
    :vartype bot_loggedIn: bool
    :var storeUsers: Whether or not to track users with botState
    :vartype storeUsers: bool
    :var storeGuilds: Whether or not to track guilds with botState
    :vartype storeGuilds: bool
    :var storeMenus: Whether or not to track reaction menus with botState
    :vartype storeMenus: bool
    :var storeNone: True if none of storeUsers, storeGuilds and storeMenus are True
    :vartype storeNone: bool
    :var launchTime: The time that the client was instanciated
    :vartype launchTime: datetime
    :var killer: Indicator of when OS termination signals are received
    :vartype killer: GracefulKiller
    """

    def __init__(self, storeUsers: bool = True, storeGuilds: bool = True, storeMenus: bool = True):
        """
        :param bool storeUsers: Whether or not to track users with botState (default True)
        :param bool storeGuilds: Whether or not to track guilds with botState (default True)
        :param bool storeMenus: Whether or not to track reaction menus with botState (default True)
        """
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="‎", intents=intents)
        self.loggedIn = False
        self.storeUsers = storeUsers
        self.storeGuilds = storeGuilds
        self.storeMenus = storeMenus
        self.storeNone = not(storeUsers or storeGuilds or storeMenus)
        self.launchTime = datetime.utcnow()
        self.killer = GracefulKiller()

    def saveAllDBs(self):
        """Save all of the bot's savedata to file.
        This currently saves:
        - the users database
        - the guilds database
        - the reaction menus database
        - logs
        """
        if self.storeUsers:
            lib.jsonHandler.saveDB(cfg.paths.usersDB, botState.usersDB)
        if self.storeGuilds:
            lib.jsonHandler.saveDB(cfg.paths.guildsDB, botState.guildsDB)
        if self.storeMenus:
            lib.jsonHandler.saveDB(cfg.paths.reactionMenusDB, botState.reactionMenusDB)
        botState.logger.save()
        if not self.storeNone:
            print(datetime.now().strftime("%H:%M:%S: Data saved!"))

    async def shutdown(self):
        """Cleanly prepare for, and then perform, shutdown of the bot.

        This currently:
        - expires all non-saveable reaction menus
        - logs out of discord
        - saves all savedata to file
        """
        if self.storeMenus:
            # expire non-saveable reaction menus
            menus = list(botState.reactionMenusDB.values())
            for menu in menus:
                if not menu.saveable:
                    await menu.delete()

        # log out of discord
        self.loggedIn = False
        await self.logout()
        # save bot save data
        self.saveAllDBs()
        print(datetime.now().strftime("%H:%M:%S: Shutdown complete."))
        # close the bot's aiohttp session
        await botState.httpClient.close()


####### GLOBAL VARIABLES #######

botState.logger = logging.Logger()

# interface into the discord servers
botState.client = BasedClient(storeUsers=True,
                              storeGuilds=True,
                              storeMenus=True)

# commands DB
from . import commands
botCommands = commands.loadCommands()


####### DATABASE FUNCTIONS #####

def loadUsersDB(filePath: str) -> userDB.UserDB:
    """Build a UserDB from the specified JSON file.

    :param str filePath: path to the JSON file to load. Theoretically, this can be absolute or relative.
    :return: a UserDB as described by the dictionary-serialized representation stored in the file located in filePath.
    """
    if os.path.isfile(filePath):
        return userDB.UserDB.fromDict(lib.jsonHandler.readJSON(filePath))
    return userDB.UserDB()


def loadGuildsDB(filePath: str, dbReload: bool = False) -> guildDB.GuildDB:
    """Build a GuildDB from the specified JSON file.

    :param str filePath: path to the JSON file to load. Theoretically, this can be absolute or relative.
    :return: a GuildDB as described by the dictionary-serialized representation stored in the file located in filePath.
    """
    if os.path.isfile(filePath):
        return guildDB.GuildDB.fromDict(lib.jsonHandler.readJSON(filePath))
    return guildDB.GuildDB()


async def loadReactionMenusDB(filePath: str) -> reactionMenuDB.ReactionMenuDB:
    """Build a reactionMenuDB from the specified JSON file.
    This method must be called asynchronously, to allow awaiting of discord message fetching functions.

    :param str filePath: path to the JSON file to load. Theoretically, this can be absolute or relative.
    :return: a reactionMenuDB as described by the dictionary-serialized representation stored in the file located in filePath.
    """
    if os.path.isfile(filePath):
        return await reactionMenuDB.fromDict(lib.jsonHandler.readJSON(filePath))
    return reactionMenuDB.ReactionMenuDB()


####### SYSTEM COMMANDS #######

async def err_nodm(message: discord.Message, args: str, isDM: bool):
    """Send an error message when a command is requested that cannot function outside of a guild

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: ignored
    """
    await message.channel.send("This command can only be used from inside of a server.")


####### MAIN FUNCTIONS #######


@botState.client.event
async def on_guild_join(guild: discord.Guild):
    """Create a database entry for new guilds when one is joined.
    TODO: Once deprecation databases are implemented, if guilds now store important information consider searching for them in deprecated

    :param discord.Guild guild: the guild just joined.
    """
    if botState.client.storeGuilds:
        guildExists = True
        if not botState.guildsDB.idExists(guild.id):
            guildExists = False
            botState.guildsDB.addID(guild.id)

        botState.logger.log("Main", "guild_join", "I joined a new guild! " + guild.name + "#" + str(guild.id) +
                                ("\n -- The guild was added to botState.guildsDB" if not guildExists else ""),
                                category="guildsDB", eventType="NW_GLD")


@botState.client.event
async def on_guild_remove(guild: discord.Guild):
    """Remove the database entry for any guilds the bot leaves.
    TODO: Once deprecation databases are implemented, if guilds now store important information consider moving them to deprecated.

    :param discord.Guild guild: the guild just left.
    """
    if botState.client.storeGuilds:
        guildExists = False
        if botState.guildsDB.idExists(guild.id):
            guildExists = True
            botState.guildsDB.removeID(guild.id)

        botState.logger.log("Main", "guild_remove", "I left a guild! " + guild.name + "#" + str(guild.id) +
                                ("\n -- The guild was removed from botState.guildsDB" if guildExists else ""),
                                category="guildsDB", eventType="NW_GLD")


@botState.client.event
async def on_ready():
    """Bot initialisation (called on bot login) and behaviour loops.
    Currently includes:
    - regular database saving to JSON

    TODO: Implement dynamic timedtask checking period
    """
    botState.httpClient = aiohttp.ClientSession()

    ##### EMOJI INITIALIZATION #####

    # Convert all UninitializedBasedEmojis in config to BasedEmoji
    await initializeEmojis()

    # Ensure all emojis have been initialized
    for varName, varValue in vars(cfg).items():
        if isinstance(varValue, lib.emojis.UninitializedBasedEmoji):
            raise RuntimeError("Uninitialized emoji still remains in cfg after emoji initialization: '" + varName + "'")

    # Load save data. If the specified files do not exist, an empty database will be created instead.
    botState.usersDB = loadUsersDB(cfg.paths.usersDB)
    botState.guildsDB = loadGuildsDB(cfg.paths.guildsDB)
    botState.reactionMenusDB = await loadReactionMenusDB(cfg.paths.reactionMenusDB)

    # Set help embed thumbnails
    setHelpEmbedThumbnails()

    # Schedule reaction menu expiry
    botState.reactionMenusTTDB = TimedTaskHeap()
    # Schedule database saving
    botState.dbSaveTT = TimedTask(expiryDelta=lib.timeUtil.timeDeltaFromDict(cfg.timeouts.dataSaveFrequency),
                                    autoReschedule=True, expiryFunction=botState.client.saveAllDBs)
    # Schedule BASED updates checking
    botState.updatesCheckTT = TimedTask(expiryDelta=lib.timeUtil.timeDeltaFromDict(cfg.timeouts.BASED_updateCheckFrequency),
                                        autoReschedule=True, expiryFunction=checkForUpdates)

    # Check for upates to BASED
    print("BASED " + versionInfo.BASED_VERSION + " loaded.\nClient logged in as {0.user}".format(botState.client))
    await checkForUpdates()

    # Set custom bot status
    await botState.client.change_presence(activity=discord.Game("BASED APP"))
    # bot is now logged in
    botState.client.loggedIn = True

    # Main loop: execute regular tasks while the bot is logged in
    while botState.client.loggedIn:
        if cfg.timedTaskCheckingType == "fixed":
            await asyncio.sleep(cfg.timedTaskLatenessThresholdSeconds)
        # elif cfg.timedTaskCheckingType == "dynamic":

        await botState.dbSaveTT.doExpiryCheck()
        await botState.reactionMenusTTDB.doTaskChecking()
        await botState.updatesCheckTT.doExpiryCheck()

        # termination signal received from OS. Trigger graceful shutdown with database saving
        if botState.client.killer.kill_now:
            botState.shutdown = botState.ShutDownState.shutdown
            print("shutdown signal received, shutting down...")
            await botState.client.shutdown()


@botState.client.event
async def on_message(message: discord.Message):
    """Called every time a message is sent in a server that the bot has joined
    Currently handles:
    - command calling

    :param discord.Message message: The message that triggered this command on sending
    """
    # ignore messages sent by bots
    if message.author.bot:
        return
    # Check whether the command was requested in DMs
    try:
        isDM = message.channel.guild is None
    except AttributeError:
        isDM = True
    # Get the context-relevant command prefix
    if isDM:
        commandPrefix = cfg.defaultCommandPrefix
    else:
        commandPrefix = botState.guildsDB.getGuild(message.guild.id).commandPrefix

    # For any messages beginning with commandPrefix
    if message.content.startswith(commandPrefix) and len(message.content) > len(commandPrefix):
        # replace special apostraphe characters with the universal '
        msgContent = message.content.replace("‘", "'").replace("’", "'")

        # split the message into command and arguments
        if len(msgContent[len(commandPrefix):]) > 0:
            command = msgContent[len(commandPrefix):].split(" ")[0]
            args = msgContent[len(commandPrefix) + len(command) + 1:]
        # if no command is given, ignore the message
        else:
            return

        # infer the message author's permissions
        accessLevel = inferUserPermissions(message)
        try:
            # Call the requested command
            commandFound = await botCommands.call(command, message, args, accessLevel, isDM=isDM)
        # If a non-DMable command was called from DMs, send an error message
        except lib.exceptions.IncorrectCommandCallContext:
            await err_nodm(message, "", isDM)
            return

        # If the command threw an exception
        except Exception as e:
            # print a user friendly error
            await message.channel.send("An unexpected error occured when calling this command. The error has been logged." +
                                        "\nThis command probably won't work until we've looked into it.")
            # log the exception as misc
            botState.logger.log("Main", "on_message", "An unexpected error occured when calling command '" +
                                command + "' with args '" + args + "': " + type(e).__name__, trace=traceback.format_exc())
            print(traceback.format_exc())
            commandFound = True

        # Command not found, send an error message.
        if not commandFound:
            await message.channel.send(":question: Unknown command. Type `" + commandPrefix + "help` for a list of commands.")


@botState.client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """Called every time a reaction is added to a message.
    If the message is a reaction menu, and the reaction is an option for that menu, trigger the menu option's behaviour.

    :param discord.RawReactionActionEvent payload: An event describing the message and the reaction added
    """
    # ignore bot reactions
    if payload.user_id != botState.client.user.id:
        # Get rich, useable reaction data
        _, user, emoji = await lib.discordUtil.reactionFromRaw(payload)
        if None in [user, emoji]:
            return

        # If the message reacted to is a reaction menu
        if payload.message_id in botState.reactionMenusDB and \
                botState.reactionMenusDB[payload.message_id].hasEmojiRegistered(emoji):
            # Envoke the reacted option's behaviour
            await botState.reactionMenusDB[payload.message_id].reactionAdded(emoji, user)


@botState.client.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    """Called every time a reaction is removed from a message.
    If the message is a reaction menu, and the reaction is an option for that menu, trigger the menu option's behaviour.

    :param discord.RawReactionActionEvent payload: An event describing the message and the reaction removed
    """
    # ignore bot reactions
    if payload.user_id != botState.client.user.id:
        # Get rich, useable reaction data
        _, user, emoji = await lib.discordUtil.reactionFromRaw(payload)
        if None in [user, emoji]:
            return

        # If the message reacted to is a reaction menu
        if payload.message_id in botState.reactionMenusDB and \
                botState.reactionMenusDB[payload.message_id].hasEmojiRegistered(emoji):
            # Envoke the reacted option's behaviour
            await botState.reactionMenusDB[payload.message_id].reactionRemoved(emoji, user)


@botState.client.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    """Called every time a message is deleted.
    If the message was a reaction menu, deactivate and unschedule the menu.

    :param discord.RawMessageDeleteEvent payload: An event describing the message deleted.
    """
    if payload.message_id in botState.reactionMenusDB:
        await botState.reactionMenusDB[payload.message_id].delete()


@botState.client.event
async def on_raw_bulk_message_delete(payload: discord.RawBulkMessageDeleteEvent):
    """Called every time a group of messages is deleted.
    If any of the messages were a reaction menus, deactivate and unschedule those menus.

    :param discord.RawBulkMessageDeleteEvent payload: An event describing all messages deleted.
    """
    for msgID in payload.message_ids:
        if msgID in botState.reactionMenusDB:
            await botState.reactionMenusDB[msgID].delete()


def run():
    """Runs the bot. Ensure that prior to importing this module, you have initialized your bot config
    by running cfg.configurator.init()

    :return: A description of what behaviour should follow shutdown
    :rtype: int
    """
    # Ensure a bot token is provided
    if not (bool(cfg.botToken) ^ bool(cfg.botToken_envVarName)):
        raise ValueError("You must give exactly one of either cfg.botToken or cfg.botToken_envVarName")

    if cfg.botToken_envVarName and cfg.botToken_envVarName not in os.environ:
        raise KeyError("Bot token environment variable " + cfg.botToken_envVarName + " not set (cfg.botToken_envVarName")

    # Launch the bot!! 🤘🚀
    botState.client.run(cfg.botToken if cfg.botToken else os.environ[cfg.botToken_envVarName])
    return botState.shutdown
