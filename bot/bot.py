# Discord Imports

import discord
from discord.ext.commands import Bot as ClientBaseClass
 

# Util imports

from datetime import datetime
import os
import traceback
import asyncio
import aiohttp
import sys
import signal
import time


# BASED Imports

from . import lib, botState, logging
from .databases import guildDB, reactionMenuDB, userDB
from .scheduling import TimedTaskHeap, TimedTask
from .cfg import cfg, versionInfo


async def checkForUpdates():
    """Check if any new BASED versions are available, and print a message to console if one is found.
    """
    try:
        BASED_versionCheck = await versionInfo.checkForUpdates(botState.httpClient)
    except versionInfo.UpdatesCheckFailed:
        print("⚠ BASED updates check failed. Either the GitHub API is down, or your BASED updates checker version is depracated: " + versionInfo.BASED_REPO_URL)
    else:
        if BASED_versionCheck.updatesChecked and not BASED_versionCheck.upToDate:
            print("⚠ New BASED update " + BASED_versionCheck.latestVersion + " now available! See " + versionInfo.BASED_REPO_URL + " for instructions on how to update your BASED fork.")


class GracefulKiller:
  kill_now = False
  def __init__(self):
    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)

  def exit_gracefully(self,signum, frame):
    self.kill_now = True


class BasedClient(ClientBaseClass):
    """A minor extension to discord.ext.commands.Bot to include database saving and extended shutdown procedures.

    A command_prefix is assigned to this bot, but no commands are registered to it, so this is effectively meaningless.
    I chose to assign a zero-width character, as this is unlikely to ever be chosen as the bot's actual command prefix, minimising erroneous commands.Bot command recognition. 
    
    :var bot_loggedIn: Tracks whether or not the bot is currently logged in
    :type bot_loggedIn: bool
    """
    def __init__(self, storeUsers=True, storeGuilds=True, storeMenus=True):
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
        """
        if self.storeUsers:
            lib.jsonHandler.saveDB(cfg.userDBPath, botState.usersDB)
        if self.storeGuilds:
            lib.jsonHandler.saveDB(cfg.guildDBPath, botState.guildsDB)
        if self.storeMenus:
            lib.jsonHandler.saveDB(cfg.reactionMenusDBPath, botState.reactionMenusDB)
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
        for guild in botState.guildsDB.getGuilds():
            for game in guild.runningGames.values():
                game.shutdownOverride = True
                game.shutdownOverrideReason = "The bot is shutting down"

        if self.storeMenus:
            menus = list(botState.reactionMenusDB.values())
            for menu in menus:
                if not menu.saveable:
                    await menu.delete()
        self.loggedIn = False
        await self.logout()
        self.saveAllDBs()
        await botState.httpClient.close()
        print(datetime.now().strftime("%H:%M:%S: Shutdown complete."))



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

def loadUsersDB(filePath : str) -> userDB.UserDB:
    """Build a UserDB from the specified JSON file.

    :param str filePath: path to the JSON file to load. Theoretically, this can be absolute or relative.
    :return: a UserDB as described by the dictionary-serialized representation stored in the file located in filePath.
    """
    if os.path.isfile(filePath):
        return userDB.UserDB.fromDict(lib.jsonHandler.readJSON(filePath))
    return userDB.UserDB()


def loadGuildsDB(filePath : str, dbReload : bool = False) -> guildDB.GuildDB:
    """Build a GuildDB from the specified JSON file.

    :param str filePath: path to the JSON file to load. Theoretically, this can be absolute or relative.
    :return: a GuildDB as described by the dictionary-serialized representation stored in the file located in filePath.
    """
    if os.path.isfile(filePath):
        return guildDB.GuildDB.fromDict(lib.jsonHandler.readJSON(filePath))
    return guildDB.GuildDB()


async def loadReactionMenusDB(filePath : str) -> reactionMenuDB.ReactionMenuDB:
    """Build a reactionMenuDB from the specified JSON file.
    This method must be called asynchronously, to allow awaiting of discord message fetching functions.

    :param str filePath: path to the JSON file to load. Theoretically, this can be absolute or relative.
    :return: a reactionMenuDB as described by the dictionary-serialized representation stored in the file located in filePath.
    """
    if os.path.isfile(filePath):
        return await reactionMenuDB.fromDict(lib.jsonHandler.readJSON(filePath))
    return reactionMenuDB.ReactionMenuDB()


####### SYSTEM COMMANDS #######

async def err_nodm(message : discord.Message, args : str, isDM : bool):
    """Send an error message when a command is requested that cannot function outside of a guild

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: ignored
    """
    await message.channel.send("This command can only be used from inside of a server.")


####### MAIN FUNCTIONS #######



@botState.client.event
async def on_guild_join(guild : discord.Guild):
    """Create a database entry for new guilds when one is joined.
    TODO: Once deprecation databases are implemented, if guilds now store important information consider searching for them in deprecated

    :param discord.Guild guild: the guild just joined.
    """
    if botState.client.storeGuilds:
        guildExists = True
        if not botState.guildsDB.idExists(guild.id):
            guildExists = False
            botState.guildsDB.addID(guild.id)
        botState.logger.log("Main", "guild_join", "I joined a new guild! " + guild.name + "#" + str(guild.id) + ("\n -- The guild was added to botState.guildsDB" if not guildExists else ""),
                    category="guildsDB", eventType="NW_GLD")


@botState.client.event
async def on_guild_remove(guild : discord.Guild):
    """Remove the database entry for any guilds the bot leaves.
    TODO: Once deprecation databases are implemented, if guilds now store important information consider moving them to deprecated.

    :param discord.Guild guild: the guild just left.
    """
    if botState.client.storeGuilds:
        guildExists = False
        if botState.guildsDB.idExists(guild.id):
            guildExists = True
            botState.guildsDB.removeID(guild.id)
        botState.logger.log("Main", "guild_remove", "I left a guild! " + guild.name + "#" + str(guild.id) + ("\n -- The guild was removed from botState.guildsDB" if guildExists else ""),
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
    # Iterate over uninitiaizedEmoji attributes in cfg
    for varName, varValue in vars(cfg).items():
        if isinstance(varValue, lib.emojis.UninitializedBasedEmoji):
            uninitEmoji = varValue.value
            # Create BasedEmoji instances based on the type of the uninitialized value
            if isinstance(uninitEmoji, int):
                setattr(cfg, varName, lib.emojis.BasedEmoji(id=uninitEmoji))
            elif isinstance(uninitEmoji, str):
                setattr(cfg, varName, lib.emojis.BasedEmoji.fromStr(uninitEmoji))
            elif isinstance(uninitEmoji, dict):
                setattr(cfg, varName, lib.emojis.BasedEmoji.fromDict(uninitEmoji))
            # Unrecognised uninitialized value
            else:
                raise ValueError("Unrecognised UninitializedBasedEmoji value type. Expecting int, str or dict, given '" + type(uninitEmoji).__name__ + "'")
    
    # Ensure all emojis have been initialized
    for varName, varValue in vars(cfg).items():
        if isinstance(varValue, lib.emojis.UninitializedBasedEmoji):
            raise RuntimeError("Uninitialized emoji still remains in cfg after emoji initialization: '" + varName + "'")

    botState.usersDB = loadUsersDB(cfg.userDBPath)
    botState.guildsDB = loadGuildsDB(cfg.guildDBPath)

    # Handle any guilds joined while the bot was offline
    for guild in botState.client.guilds:
        if not botState.guildsDB.idExists(guild.id):
            botState.guildsDB.addID(guild.id)

    # Set help embed thumbnails
    for levelSection in botCommands.helpSectionEmbeds:
        for helpSection in levelSection.values():
            for embed in helpSection:
                embed.set_thumbnail(url=botState.client.user.avatar_url_as(size=64))

    botState.reactionMenusTTDB = TimedTaskHeap.TimedTaskHeap()
    if not os.path.exists(cfg.reactionMenusDBPath):
        try:
            f = open(cfg.reactionMenusDBPath, 'x')
            f.write("{}")
            f.close()
        except IOError as e:
            botState.logger.log("main","on_ready","IOError creating reactionMenuDB save file: " + e.__class__.__name__, trace=traceback.format_exc())

    botState.reactionMenusDB = await loadReactionMenusDB(cfg.reactionMenusDBPath)

    botState.dbSaveTT = TimedTask.TimedTask(expiryDelta=lib.timeUtil.timeDeltaFromDict(cfg.savePeriod), autoReschedule=True, expiryFunction=botState.client.saveAllDBs)
    botState.updatesCheckTT = TimedTask.TimedTask(expiryDelta=lib.timeUtil.timeDeltaFromDict(cfg.BASED_updateCheckFrequency), autoReschedule=True, expiryFunction=checkForUpdates)

    print("BASED " + versionInfo.BASED_VERSION + " loaded.\nClient logged in as {0.user}".format(botState.client))
    await checkForUpdates()

    await botState.client.change_presence(activity=discord.Game("BASED APP"))
    # bot is now logged in
    botState.client.loggedIn = True

    # execute regular tasks while the bot is logged in
    while botState.client.loggedIn:
        if cfg.timedTaskCheckingType == "fixed":
            await asyncio.sleep(cfg.timedTaskLatenessThresholdSeconds)
        # elif cfg.timedTaskCheckingType == "dynamic":

        await botState.dbSaveTT.doExpiryCheck()
        await botState.reactionMenusTTDB.doTaskChecking()
        await botState.updatesCheckTT.doExpiryCheck()

        if botState.client.killer.kill_now:
            botState.shutdown = True
            print("shutdown signal received, shutting down...")
            await botState.client.shutdown()


@botState.client.event
async def on_message(message : discord.Message):
    """Called every time a message is sent in a server that the bot has joined
    Currently handles:
    - command calling

    :param discord.Message message: The message that triggered this command on sending
    """
    # ignore messages sent by bots
    if message.author.bot:
        return

    # Check whether the command was requested in DMs
    isDM = message.channel.type in [discord.ChannelType.private, discord.ChannelType.group]

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
        if message.author.id in cfg.developers:
            accessLevel = 3
        elif message.author.permissions_in(message.channel).administrator:
            accessLevel = 2
        else:
            accessLevel = 0

        try:
            # Call the requested command
            commandFound = await botCommands.call(command, message, args, accessLevel, isDM=isDM)
        
        # If a non-DMable command was called from DMs, send an error message 
        except lib.exceptions.IncorrectCommandCallContext:
            await err_nodm(message, "", isDM)
            return

        # If the command threw an exception, print a user friendly error and log the exception as misc.
        except Exception as e:
            await message.channel.send("An unexpected error occured when calling this command. The error has been logged.\nThis command probably won't work until we've looked into it.")
            botState.logger.log("Main", "on_message", "An unexpected error occured when calling command '" +
                            command + "' with args '" + args + "': " + type(e).__name__, trace=traceback.format_exc())
            print(traceback.format_exc())
            commandFound = True

        # Command not found, send an error message.
        if not commandFound:
            await message.channel.send(":question: Unknown command. Type `" + commandPrefix + "help` for a list of commands.")


@botState.client.event
async def on_raw_reaction_add(payload : discord.RawReactionActionEvent):
    """Called every time a reaction is added to a message.
    If the message is a reaction menu, and the reaction is an option for that menu, trigger the menu option's behaviour.

    :param discord.RawReactionActionEvent payload: An event describing the message and the reaction added
    """
    if payload.user_id != botState.client.user.id:
        _, user, emoji = await lib.discordUtil.reactionFromRaw(payload)
        if None in [user, emoji]:
            return

        if payload.message_id in botState.reactionMenusDB and \
                botState.reactionMenusDB[payload.message_id].hasEmojiRegistered(emoji):
            await botState.reactionMenusDB[payload.message_id].reactionAdded(emoji, user)


@botState.client.event
async def on_raw_reaction_remove(payload : discord.RawReactionActionEvent):
    """Called every time a reaction is removed from a message.
    If the message is a reaction menu, and the reaction is an option for that menu, trigger the menu option's behaviour.

    :param discord.RawReactionActionEvent payload: An event describing the message and the reaction removed
    """
    if payload.user_id != botState.client.user.id:
        _, user, emoji = await lib.discordUtil.reactionFromRaw(payload)
        if None in [user, emoji]:
            return

        if payload.message_id in botState.reactionMenusDB and \
                botState.reactionMenusDB[payload.message_id].hasEmojiRegistered(emoji):
            await botState.reactionMenusDB[payload.message_id].reactionRemoved(emoji, user)


@botState.client.event
async def on_raw_message_delete(payload : discord.RawMessageDeleteEvent):
    """Called every time a message is deleted.
    If the message was a reaction menu, deactivate and unschedule the menu.

    :param discord.RawMessageDeleteEvent payload: An event describing the message deleted.
    """
    if payload.message_id in botState.reactionMenusDB:
        await botState.reactionMenusDB[payload.message_id].delete()


@botState.client.event
async def on_raw_bulk_message_delete(payload : discord.RawBulkMessageDeleteEvent):
    """Called every time a group of messages is deleted.
    If any of the messages were a reaction menus, deactivate and unschedule those menus.

    :param discord.RawBulkMessageDeleteEvent payload: An event describing all messages deleted.
    """
    for msgID in payload.message_ids:
        if msgID in botState.reactionMenusDB:
            await botState.reactionMenusDB[msgID].delete()


for varName in ["SDB_DC_TOKEN"]:
    if varName not in os.environ:
        raise KeyError("required environment variable " + varName + " not set.")

# Launch the bot!! 🤘🚀
botState.client.run(os.environ["SDB_DC_TOKEN"])

sys.exit(int(botState.shutdown))