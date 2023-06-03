# Set up bot config

from typing import Literal, Optional, cast
from .cfg import cfg

# Discord Imports

import discord # type: ignore[import]
from discord import ClientUser, Member, app_commands, Interaction
from discord.ext.commands import ExtensionNotLoaded
from discord.abc import GuildChannel


# Util imports

import os
import traceback
import asyncio

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession


# BASED Imports

from . import lib, botState
from .lib import BASED_version
from .lib.sql import SessionSharer
from .client import BasedClient
from .logging import LogCategory
from .users.basedGuild import BasedGuild
from .interactions import basedComponent

from .repositories.guildRepository import GuildRepository
from .repositories.reactionMenuRepository import ReactionMenuRepository


def setHelpEmbedThumbnails():
    """Loads the bot application's profile picture into all help menu embeds as the embed thumbnail.
    If no profile picture is set for the application, the default profile picture is used instead.
    """
    if botState.client.user is None:
        raise ValueError("Cannot set help embed thumbs because the client is not yet logged in")
    avatar = botState.client.user.display_avatar.url
    for levelSection in botCommands.helpSectionEmbeds:
        for helpSection in levelSection.values():
            for embed in helpSection:
                embed.set_thumbnail(url=avatar)


def inferUserPermissions(message: discord.Message) -> int:
    """Get the commands access level of the user that sent the given message.
    
    :return: message.author's access level, as an index of cfg.userAccessLevels
    :rtype: int
    """
    if message.author.id in cfg.developers:
        return 3
    # Performing a Member cast here, because we already know that the channel is in a guild, so the author must be a member.
    elif isinstance(message.channel, GuildChannel) and message.channel.permissions_for(cast(Member, message.author)).administrator:
        return 2
    else:
        return 0



####### GLOBAL VARIABLES #######

# Ensure a connection string token is provided
if not (bool(cfg.databaseConnectionString) ^ bool(cfg.databaseConnectionString_envVarName)):
    raise ValueError("You must give exactly one of either cfg.databaseConnectionString or cfg.databaseConnectionString_envVarName")

if cfg.databaseConnectionString_envVarName and cfg.databaseConnectionString_envVarName not in os.environ:
    raise KeyError(f"Bot token environment variable {cfg.databaseConnectionString_envVarName} not set (cfg.databaseConnectionString_envVarName")

# interface into the discord servers
engine = create_async_engine(
    # mysql+asyncmy://root:{os.environ['BB_MYSQL_PASS']}@localhost:3306/bountybot
    cfg.databaseConnectionString if cfg.databaseConnectionString else os.environ[cfg.databaseConnectionString_envVarName],
    # echo=True
)

botState.client = BasedClient(engine)

async def loadExtensions():
    for c in cfg.includedCogs:
        await botState.client.load_extension(c)


# commands DB
from . import commands
botCommands = commands.loadCommands()



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
    guildExists = True
    async with botState.client.sessionMaker() as session:
        guilds = GuildRepository(session)
        if not await guilds.exists(guild.id):
            guildExists = False
            await guilds.create(BasedGuild(id=guild.id))

    botState.client.logger.log("Main", "guild_join", f"I joined a new guild! {guild.name}#{guild.id}" +
                            ("\n -- The guild was added to the database" if not guildExists else ""),
                            category=LogCategory.guildsDB, eventType="NW_GLD")


@botState.client.event
async def on_guild_remove(guild: discord.Guild):
    """Remove the database entry for any guilds the bot leaves.
    TODO: Once deprecation databases are implemented, if guilds now store important information consider moving them to deprecated.

    :param discord.Guild guild: the guild just left.
    """
    guildExists = False
    async with botState.client.sessionMaker() as session:
        guilds = GuildRepository(session)
        if await guilds.exists(guild.id):
            guildExists = True
            await guilds.delete(guild.id)

    botState.client.logger.log("Main", "guild_remove", f"I left a guild! {guild.name}#{guild.id}" +
                            ("\n -- The guild was removed from database" if guildExists else ""),
                            category=LogCategory.guildsDB, eventType="NW_GLD")


@botState.client.event
async def on_ready():
    # Set help embed thumbnails
    setHelpEmbedThumbnails()

    print("BASED " + BASED_version.BASED_VERSION + " loaded.\nClient logged in as {0.user}".format(botState.client))

    # Set custom bot status
    await botState.client.change_presence(activity=discord.Game("BASED APP"))

    # Convert all UninitializedBasedEmojis in config to BasedEmoji
    cfg.defaultEmojis.initializeEmojis()
    # Create missing directories
    cfg.paths.createMissingDirectories()


@botState.client.event
async def on_message(message: discord.Message):
    """Called every time a message is sent in a server that the bot has joined
    Currently handles:
    - command calling

    :param discord.Message message: The message that triggered this command on sending
    """
    if not botState.client.loggedIn:
        return
        
    # ignore messages sent by bots
    if message.author.bot:
        return
    
    if message.guild is None:
        isDM = True
        commandPrefix = cfg.defaultCommandPrefix
    else:
        isDM = False
        async with botState.client.sessionMaker() as session:
            guilds = GuildRepository(session)
            commandPrefix = await guilds.getCommandPrefix(message.guild.id) or cfg.defaultCommandPrefix

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
            botState.client.logger.log("Main", "on_message", "An unexpected error occured when calling command '" +
                                command + "' with args '" + args + "': " + type(e).__name__, trace=traceback.format_exc())
            print(traceback.format_exc())
            commandFound = True

        # Command not found, send an error message.
        if not commandFound:
            await message.channel.send(f"{cfg.defaultEmojis.error} Unknown command. " \
                                        + f"Type `{commandPrefix}help` for a list of commands.")


@botState.client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """Called every time a reaction is added to a message.
    If the message is a reaction menu, and the reaction is an option for that menu, trigger the menu option's behaviour.

    :param discord.RawReactionActionEvent payload: An event describing the message and the reaction added
    """
    if not botState.client.loggedIn: return

    # ignore bot reactions
    # ignoring a warning here that Client.user can be None, if the client is not logged in.
    # The client will always be logged in here, because this event can only be triggered by discord reactions.
    if payload.user_id == cast(ClientUser, botState.client.user).id: return

    _, user, emoji = await lib.discordUtil.reactionFromRaw(payload)
    if user is None or emoji is None or isinstance(user, ClientUser): return

    async with botState.client.sessionMaker() as session:
        menusRepo = ReactionMenuRepository(session)

        menu = botState.client.inMemoryReactionMenusDB.get(payload.message_id, None) \
                or await menusRepo.get(payload.message_id)
        
        if menu is None: return
        
        hasEmoji = await menu.hasEmoji(emoji, session=session)
        if not hasEmoji: return
        
        await menu.reactionAdded(botState.client, emoji, user, session=session)


@botState.client.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    """Called every time a reaction is removed from a message.
    If the message is a reaction menu, and the reaction is an option for that menu, trigger the menu option's behaviour.

    :param discord.RawReactionActionEvent payload: An event describing the message and the reaction removed
    """
    if not botState.client.loggedIn: return
        
    # Get rich, useable reaction data
    _, user, emoji = await lib.discordUtil.reactionFromRaw(payload)
    if user is None or emoji is None or isinstance(user, ClientUser): return

    async with botState.client.sessionMaker() as session:
        menusRepo = ReactionMenuRepository(session)
        menu = botState.client.inMemoryReactionMenusDB.get(payload.message_id, None) \
                or await menusRepo.get(payload.message_id)
        
        if menu is not None and await menu.hasEmoji(emoji, session=session):
            await menu.reactionRemoved(botState.client, emoji, user, session=session)


async def tryEndMenu(menuId: int, repository: ReactionMenuRepository):
    menu = botState.client.inMemoryReactionMenusDB.get(menuId, None) \
            or await repository.get(menuId)
    
    if menu is not None:
        await menu.end(botState.client, session=repository.session)


@botState.client.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    """Called every time a message is deleted.
    If the message was a reaction menu, deactivate and unschedule the menu.

    :param discord.RawMessageDeleteEvent payload: An event describing the message deleted.
    """
    if not botState.client.loggedIn: return
    
    async with botState.client.sessionMaker() as session:
        menusRepo = ReactionMenuRepository(session)
        await tryEndMenu(payload.message_id, menusRepo)


@botState.client.event
async def on_raw_bulk_message_delete(payload: discord.RawBulkMessageDeleteEvent):
    """Called every time a group of messages is deleted.
    If any of the messages were a reaction menus, deactivate and unschedule those menus.

    :param discord.RawBulkMessageDeleteEvent payload: An event describing all messages deleted.
    """
    if not botState.client.loggedIn: return

    tasks = lib.discordUtil.BasicScheduler()
    
    async with botState.client.sessionMaker() as session:
        menusRepo = ReactionMenuRepository(session)
        for msgID in payload.message_ids:
            tasks.add(tryEndMenu(msgID, menusRepo))

    await tasks.wait()
    tasks.logExceptions()


def removeViewFromMessageCallback(message: discord.Message):
    async def removeViewFromMessage(interaction: Interaction):
        await message.edit(content="🛑 Cancelled.", view=None)
    return removeViewFromMessage


def loadExtensionCallback(extensionName: str):
    async def loadExtension(interaction: Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await botState.client.load_extension(extensionName)
        except Exception as e:
            await interaction.followup.send(f"{type(e).__name__}: {e}", ephemeral=True)
        else:
            await interaction.followup.send(f"reloaded successfully!", ephemeral=True)
    return loadExtension


@botState.client.basedCommand(accessLevel=cfg.basicAccessLevels.developer, helpSection="extensions")
@app_commands.command(name="reload-extension",
                        description="Unload and re-load a cog or other extension.")
@app_commands.guilds(*cfg.developmentGuilds)
async def dev_cmd_reload_extension(interaction: Interaction, extension_name: str):
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await botState.client.reload_extension(extension_name)
    except ExtensionNotLoaded:
        view = discord.ui.View()
        cancelButton = discord.ui.Button(style=discord.ButtonStyle.red, label="cancel")
        cancelButton.callback = removeViewFromMessageCallback(await interaction.original_response())
        acceptButton = discord.ui.Button(style=discord.ButtonStyle.green, label="load")
        acceptButton.callback = loadExtensionCallback(extension_name)
        view.add_item(cancelButton).add_item(acceptButton)
        await interaction.followup.send("No such extension is currently loaded. Load it?", ephemeral=True, view=view)
    except Exception as e:
        await interaction.followup.send(f"{type(e).__name__}: {e}", ephemeral=True)
    else:
        await interaction.followup.send(f"reloaded successfully!", ephemeral=True)

botState.client.tree.add_command(dev_cmd_reload_extension, guilds=cfg.developmentGuilds)


@botState.client.basedCommand(accessLevel=cfg.basicAccessLevels.developer, helpSection="extensions")
@app_commands.command(name="unload-extension",
                        description="Unload a cog or other extension.")
@app_commands.guilds(*cfg.developmentGuilds)
async def dev_cmd_unload_extension(interaction: Interaction, extension_name: str):
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await botState.client.unload_extension(extension_name)
    except Exception as e:
        await interaction.followup.send(f"{type(e).__name__}: {e}", ephemeral=True)
    else:
        await interaction.followup.send(f"unloaded successfully!", ephemeral=True)

botState.client.tree.add_command(dev_cmd_unload_extension, guilds=cfg.developmentGuilds)


@botState.client.basedCommand(accessLevel=cfg.basicAccessLevels.developer, helpSection="commands",
                        formattedDesc="Sync app commands with guilds. Give no args to sync global commands, or give exactly one of `spec` or `guilds`",
                        formattedParamDescs=dict(spec="`here` to sync this guild, `copy to here` to copy global commands to this guild and sync"))
@app_commands.command(name="sync",
                        description="Sync app commands with guilds. Give no args to sync global commands, or give one of 'spec'/'guilds'")
@app_commands.describe(guilds="comma separated list of guild IDs to sync",
                        spec="'here' to sync this guild, 'copy to here' to copy global commands to this guild and sync")
@app_commands.guilds(*cfg.developmentGuilds)
async def dev_cmd_sync_app_commands(interaction: Interaction, guilds: Optional[str] = None, spec: Optional[Literal["here", "copy to here"]] = None) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)
    if not guilds:
        if not spec:
            fmt = await botState.client.tree.sync()
            await interaction.followup.send(f"Synced {len(fmt)} commands globally")
        else:
            if interaction.guild is None:
                await interaction.followup.send("The spec option is only valid when used from within a guild")
                return
            if spec == "copy to here":
                botState.client.tree.copy_global_to(guild=interaction.guild)
            fmt = await botState.client.tree.sync(guild=interaction.guild)
            await interaction.followup.send(f"{'Copied' if spec == 'copy to here' else 'Synced'} {len(fmt)} commands to the current guild")
        return

    synced = []
    async def syncGuild(guild):
        try:
            await botState.client.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            synced.append(None) # stupid scoping workaround, can't use an int

    _guilds = set(map(lambda x: discord.Object(int(x)), guilds.split(", ")))

    tasks = lib.discordUtil.BasicScheduler()
    for guild in _guilds:
        tasks.add(syncGuild(guild))
    
    if tasks.any():
        await tasks.wait()
        if exceptions := tasks.getExceptions():
            tasks.logExceptions()
            await interaction.followup.send(f"Synced the tree to {len(synced)}/{len(_guilds)} guilds. {len(exceptions)} guild(s) failed to sync, exceptions have been logged.")
        else:
            await interaction.followup.send(f"Synced the tree to {len(synced)}/{len(_guilds)} guilds.")
    else:
        await interaction.followup.send(f"No syncing was performed: No guilds to sync to")

botState.client.tree.add_command(dev_cmd_sync_app_commands, guilds=cfg.developmentGuilds)


async def dev_cmd_initialSync(message: discord.Message, args: str, isDM: bool):
    view = discord.ui.View()
    deleteButton = discord.ui.Button(style=discord.ButtonStyle.red, emoji="🧺")
    deleteButton = basedComponent.StaticComponents.Delete_Message(deleteButton)
    view.add_item(deleteButton)

    if message.guild is None or not any(g.id == message.guild.id for g in cfg.developmentGuilds):
        await message.reply(":x: This command can only be used from a development guild.", view=view)
        return

    synced = await botState.client.tree.sync(guild=message.guild)

    await message.reply(f"✅ Synced {len(synced)} command(s) to this guild")

botCommands.register("initialSync", dev_cmd_initialSync, cfg.userAccessLevels.index(cfg.basicAccessLevels.developer), allowDM=False)


async def runAsync():
    """Runs the bot.
    If you wish to use a toml config file, ensure that you have loaded it first with carica.loadCfg.

    :return: A description of what behaviour should follow shutdown
    :rtype: int
    """
    # Ensure a bot token is provided
    if not (bool(cfg.botToken) ^ bool(cfg.botToken_envVarName)):
        raise ValueError("You must give exactly one of either cfg.botToken or cfg.botToken_envVarName")

    if cfg.botToken_envVarName and cfg.botToken_envVarName not in os.environ:
        raise KeyError("Bot token environment variable " + cfg.botToken_envVarName + " not set (cfg.botToken_envVarName")

    async with botState.client:
        await loadExtensions()
        # Launch bot
        await botState.client.start(cfg.botToken if cfg.botToken else os.environ[cfg.botToken_envVarName])
    
    return botState.client.shutDownState


def run():
    """Runs the bot.
    If you wish to use a toml config file, ensure that you have loaded it first with carica.loadCfg.

    :return: A description of what behaviour should follow shutdown
    :rtype: int
    """
    return asyncio.run(runAsync())
