import asyncio
from inspect import iscoroutinefunction
import signal
from typing import List, Optional, Dict, Tuple, Type, Union, overload
import aiohttp
import discord # type: ignore[import]
from discord import app_commands
from discord.ext.commands import Bot as ClientBaseClass # type: ignore[import]
from discord.ext import tasks # type: ignore[import]
from discord.utils import MISSING # type: ignore[import]
from datetime import datetime, timedelta

from .interactions import accessLevels, commandChecks
from .databases import userDB, guildDB, reactionMenuDB
import os
from . import lib
from .cfg import cfg
from . import logging
from .scheduling import timedTaskHeap
from .interactions import basedCommand, basedComponent, basedApp


class ShutDownState:
    restart = 0
    shutdown = 1
    update = 2


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


def loadUsersDB(filePath: str) -> userDB.UserDB:
    """Build a UserDB from the specified JSON file.

    :param str filePath: path to the JSON file to load. Theoretically, this can be absolute or relative.
    :return: a UserDB as described by the dictionary-serialized representation stored in the file located in filePath.
    """
    if os.path.isfile(filePath):
        return userDB.UserDB.deserialize(lib.jsonHandler.readJSON(filePath))
    return userDB.UserDB()


def loadGuildsDB(filePath: str, dbReload: bool = False) -> guildDB.GuildDB:
    """Build a GuildDB from the specified JSON file.

    :param str filePath: path to the JSON file to load. Theoretically, this can be absolute or relative.
    :return: a GuildDB as described by the dictionary-serialized representation stored in the file located in filePath.
    """
    if os.path.isfile(filePath):
        return guildDB.GuildDB.deserialize(lib.jsonHandler.readJSON(filePath))
    return guildDB.GuildDB()


async def loadReactionMenusDB(filePath: str) -> reactionMenuDB.ReactionMenuDB:
    """Build a reactionMenuDB from the specified JSON file.
    This method must be called asynchronously, to allow awaiting of discord message fetching functions.

    :param str filePath: path to the JSON file to load. Theoretically, this can be absolute or relative.
    :return: a reactionMenuDB as described by the dictionary-serialized representation stored in the file located in filePath.
    """
    if os.path.isfile(filePath):
        return await reactionMenuDB.deserialize(lib.jsonHandler.readJSON(filePath))
    return reactionMenuDB.ReactionMenuDB()


def waitBeforeStartingTask(task: tasks.Loop):
    async def inner():
        await asyncio.sleep(timedelta(seconds=task.seconds, minutes=task.minutes, hours=task.hours).total_seconds())
    
    task.before_loop(inner)
    return task


class BasedClient(ClientBaseClass):
    """A minor extension to discord.ext.commands.Bot to include database saving and extended shutdown procedures.

    A command_prefix is assigned to this bot, but no commands are registered to it, so this is effectively meaningless.
    I chose to assign a zero-width character, as this is unlikely to ever be chosen as the bot's actual command prefix,
    minimising erroneous commands.Bot command recognition. 

    :var bot_loggedIn: Tracks whether or not the bot is currently logged in
    :vartype bot_loggedIn: bool
    :vartype launchTime: datetime
    :var killer: Indicator of when OS termination signals are received
    :vartype killer: GracefulKiller
    """

    def __init__(self, usersDB: Optional[userDB.UserDB] = None,
                        guildsDB: Optional[guildDB.GuildDB] = None,
                        reactionMenusDB: Optional[reactionMenuDB.ReactionMenuDB] = None,
                        logger: logging.Logger = None,
                        taskScheduler: timedTaskHeap.TimedTaskHeap = None,
                        httpClient: aiohttp.ClientSession = None):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="‎", intents=intents)

        self._usersDB = usersDB
        self._guildsDB = guildsDB
        self._reactionMenusDB = reactionMenusDB
        self._dbsLoaded = None not in (usersDB, guildsDB, reactionMenusDB)

        self.loggedIn = False
        self.launchTime = discord.utils.utcnow()
        self.killer = GracefulKiller()

        self.taskScheduler = taskScheduler
        self._schedulerLoaded = taskScheduler is not None
        
        self.logger = logger if logger is not None else logging.Logger()
        self.httpClient = httpClient

        self.basedCommands: Dict[discord.app_commands.Command, "basedCommand.BasedCommandMeta"] = {}
        self.staticComponentCallbacks: Dict[str, "basedApp.CallBackType"] = {}

        self.helpSections: Dict[str, List[discord.app_commands.Command]] = {}

        self.add_listener(self.on_interaction)


    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component or not basedComponent.customIdIsStaticComponent(interaction.data["custom_id"]):
            return
        meta = basedComponent.staticComponentMeta(interaction.data["custom_id"])
        if not self.hasStaticComponent(meta):
            return

        args = (interaction, meta.args)
        component = self.getStaticComponentCallback(meta)
        if basedApp.isCogApp(component):
            cogName = basedApp.getCogAppCogName(component)
            cog = self.get_cog(cogName)
            if cog is None:
                raise ValueError(f"unable to find cog '{cogName}' for static component: {component}")
            if hasattr(component, "__self__") and isinstance(component.__self__, type):
                args = (cog.__class__,) + args
            else:
                args = (cog,) + args

        await component(*args)


    def addBasedCommand(self, command: discord.app_commands.Command):
        """Register a based command's metadata with the bot.
        This does not register for command calling. Use the default discord.py behaviour for this.

        :param command: The command to register
        :type command: discord.app_commands.Command
        :raises KeyError: If the command is already registered
        :raises ValueError: If the command has not been made into a BASED command with the `basedCommand` decorator
        """
        if basedApp.appType(command.callback) != basedApp.BasedAppType.AppCommand:
            raise ValueError(f"command {command.qualified_name} is not a BASED command")
        if command in self.basedCommands:
            raise KeyError(f"Command {command.qualified_name} is already registered")
        meta = basedCommand.commandMeta(command)
        self.basedCommands[command] = meta
        if meta.helpSection not in self.helpSections:
            self.helpSections[meta.helpSection] = [command]
        else:
            self.helpSections[meta.helpSection].append(command)


    def addStaticComponent(self, callback: "basedApp.CallBackType"):
        """Register a static component callback's metadata with the bot.
        This enables static component behaviour as described by the `staticComponentCallback` decorator.

        :param callback: The static component to register
        :type command: basedApp.CallBackType
        :raises KeyError: If the component is already registered
        :raises ValueError: If the callback has not been made into a static component callback with the `staticComponentCallback` decorator
        """
        if basedApp.appType(callback) != basedApp.BasedAppType.StaticComponent:
            raise ValueError(f"callback {callback.__name__} is not a static component callback")
        
        meta = basedComponent.staticComponentCallbackMeta(callback)
        key = basedComponent.staticComponentKey(meta.category, meta.subCategory)
        if key in self.staticComponentCallbacks:
            raise KeyError(f"Static component callback {callback.__name__} is already registered")

        self.staticComponentCallbacks[key] = callback


    def basedCommand(self,
        *,
        accessLevel: Union[Type[accessLevels.AccessLevel], str] = MISSING,
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
                accessLevel = accessLevels.accessLevelNamed(accessLevel)

            basedApp.basedApp(func.callback, basedApp.BasedAppType.AppCommand)
            setattr(func.callback, "__based_command_meta__", basedCommand.BasedCommandMeta(accessLevel, showInHelp, helpSection, formattedDesc, formattedParamDescs))
            self.addBasedCommand(func)

            if accessLevel is not MISSING:
                func.add_check(commandChecks.requireAccess(accessLevel))

            return func

        return decorator

    
    def staticComponentCallback(self, *, category: str = "", subCategory: str = ""):
        """Decorator marking a coroutine as a static component callback.
        The callback for static components identifying this callback by category/subcategory will be preserved across bot restarts

        Example usage:
        ```
        @bot.staticComponentCallback(category="myCallback")
        async def myCallback(interaction: Interaction, args: str):
            await interaction.response.send_message(f"This static callback received args: {args}")

        @bot.app_commands.command(name="send-static-menu")
        async def sendStaticMenu(interaction: Interaction):
            staticButton = Button(label="send callback")
            staticButton = staticComponent(staticButton, category="myCallback", args="hello")
            view.add_item(staticButton)
            await interaction.response.send_message(view=view)
        ```
        If the `send-static-menu` app command is sent, then a message will be sent in return with a button to trigger `myCallback`.
        Clicking this button will send another message with the content "hello".
        If the bot is restarted, then the button will still work.
        This works by attaching a known `custom_id` to the button, containing the static component category/sub-category and args.

        :var category: The category of the static component
        :type category: str
        :var subCategory: The sub-category of the static component
        :type subCategory: Optional[str]
        """
        def decorator(func, category=category, subCategory=subCategory):
            if not iscoroutinefunction(func):
                raise TypeError("Decorator can only be applied to coroutines")
            if not category:
                raise ValueError("Missing required argument: category")

            basedComponent.validateParam("category", category)
            basedComponent.validateParam("subCategory", subCategory)
            
            basedApp.basedApp(func, basedApp.BasedAppType.StaticComponent)
            setattr(func, "__static_component_meta__", (category, subCategory))
            self.addStaticComponent(func)

            return func

        return decorator


    def removeBasedCommand(self, command: discord.app_commands.Command):
        """Un-register a based command's metadata from the bot.
        This does not un-register for command calling. Use the default discord.py behaviour for this.

        :param command: The command to un-register
        :type command: discord.app_commands.Command
        :raises KeyError: If the command is not registered
        :raises ValueError: If the command has not been made into a BASED command with the `basedCommand` decorator
        """
        if basedApp.appType(command.callback) != basedApp.BasedAppType.AppCommand:
            raise ValueError(f"command {command.qualified_name} is not a BASED command")
        if command not in self.basedCommands:
            raise KeyError(f"Command {command.qualified_name} is not registered")
        meta = basedCommand.commandMeta(command)
        del self.basedCommands[command]
        if meta.helpSection in self.helpSections:
            self.helpSections[meta.helpSection].remove(command)
            if len(self.helpSections[meta.helpSection]) == 0:
                del self.helpSections[meta.helpSection]


    def removeStaticComponent(self, callback: "basedApp.CallBackType"):
        """Un-register a static component callback's metadata with the bot.
        This disables static component behaviour as described by the `staticComponentCallback` decorator.

        :param callback: The static component to un-register
        :type command: basedApp.CallBackType
        :raises KeyError: If the component is not registered
        :raises ValueError: If the callback has not been made into a static component callback with the `staticComponentCallback` decorator
        """
        if basedApp.appType(callback) != basedApp.BasedAppType.StaticComponent:
            raise ValueError(f"callback {callback.__name__} is not a static component callback")
        
        meta = basedComponent.staticComponentCallbackMeta(callback)
        key = basedComponent.staticComponentKey(meta.category, meta.subCategory)
        self.removeStaticComponentByKey(key)
    
    
    def removeStaticComponentByKey(self, key: str):
        """Un-register a static component callback's metadata with the bot.
        This disables static component behaviour as described by the `staticComponentCallback` decorator.

        :param key: The identifier for the static component
        :type key: str
        :raises KeyError: If the component is not registered
        """
        if key not in self.staticComponentCallbacks:
            raise KeyError(f"Static component callback key {key} is not registered")
        
        del self.staticComponentCallbacks[key]


    def commandsInSectionForAccessLevel(self, section: str, level: accessLevels._AccessLevelBase) -> List[discord.app_commands.Command]:
        """Get the commands in help section `section` that require access level `level`

        :param section: The help section for commands to look up
        :type section: str
        :param level: The access level that commands should require
        :type level: accessLevels._AccessLevelBase
        :return: A list of commands in help section `section` requiring access level `level`
        :rtype: List[discord.app_commands.Command]
        """
        return [c for c in self.helpSections[section] if basedCommand.accessLevel(c) is level and basedCommand.commandMeta(c).showInHelp]


    def helpSectionsForAccessLevel(self, level: accessLevels._AccessLevelBase) -> Dict[str, List[discord.app_commands.Command]]:
        """Get the commands for a particular access level, organized by help section

        :param level: The access level of commands to look up
        :type level: accessLevels._AccessLevelBase
        :return: The commands that require `level`, organized by help section
        :rtype: Dict[str, List[discord.app_commands.Command]]
        """
        result = {section: self.commandsInSectionForAccessLevel(section, level) for section in self.helpSections}
        return {s: c for s, c in result.items() if c}


    async def setup_hook(self):
        if self.httpClient is None:
            self.httpClient = aiohttp.ClientSession()

    
    @property
    def usersDB(self):
        """The bot's database of users.
        Databases are only available after on_ready.

        :raises lib.exceptions.NotReady: Databases not loaded yet
        :return: The bot's database of user metadata.
        :rtype: databases.userDB.UserDB
        """
        if not self._dbsLoaded:
            raise lib.exceptions.NotReady("Databases not yet loaded. BasedClient.usersDB is only available after on_ready.")
        return self._usersDB


    @property
    def guildsDB(self):
        """The bot's database of guilds.
        Databases are only available after on_ready.

        :raises lib.exceptions.NotReady: Databases not loaded yet
        :return: The bot's database of user metadata.
        :rtype: databases.guildDB.GuildDB
        """
        if not self._dbsLoaded:
            raise lib.exceptions.NotReady("Databases not yet loaded. BasedClient.usersDB is only available after on_ready.")
        return self._guildsDB


    @property
    def reactionMenusDB(self):
        """The bot's database of reaction menus.
        Databases are only available after on_ready.

        :raises lib.exceptions.NotReady: Databases not loaded yet
        :return: The bot's database of user metadata.
        :rtype: databases.reactionMenuDB.ReactionMenuDB
        """
        if not self._dbsLoaded:
            raise lib.exceptions.NotReady("Databases not yet loaded. BasedClient.usersDB is only available after on_ready.")
        return self._reactionMenusDB


    async def reloadDBs(self):
        """Save all savedata to file, and start the db saving task if it is not running.
        """
        self._usersDB = loadUsersDB(cfg.paths.usersDB)
        print(f"{len(self._usersDB.users)} users loaded")
    
        self._guildsDB = loadGuildsDB(cfg.paths.guildsDB)
        async for guild in self.fetch_guilds(limit=None):
            if not self._guildsDB.idExists(guild.id):
                self._guildsDB.addID(guild.id)
                
        print(f"{len(self._guildsDB.guilds)} guilds loaded")

        self._reactionMenusDB = await loadReactionMenusDB(cfg.paths.reactionMenusDB)

        print(f"{len(self._reactionMenusDB)} reaction menus loaded")
        
        self._dbsLoaded = True

        if not self.dbSaveTask.is_running():
            self.dbSaveTask.start()


    def saveAllDBs(self):
        """Save all of the bot's savedata to file.
        This currently saves:
        - the users database
        - the guilds database
        - the reaction menus database
        - logs
        """
        lib.jsonHandler.saveObject(cfg.paths.usersDB, self.usersDB)
        lib.jsonHandler.saveObject(cfg.paths.guildsDB, self.guildsDB)
        lib.jsonHandler.saveObject(cfg.paths.reactionMenusDB, self.reactionMenusDB)
        self.logger.save()


    async def shutdown(self):
        """Cleanly prepare for, and then perform, shutdown of the bot.

        This currently:
        - expires all non-saveable reaction menus
        - logs out of discord
        - saves all savedata to file
        """
        print("shutdown signal received, shutdown scheduled.")
        self.taskScheduler.stopTaskChecking()
        tasks = lib.discordUtil.BasicScheduler()
        # expire non-saveable reaction menus
        for menu in self.reactionMenusDB.values():
            if not menu.saveable:
                tasks.add(menu.delete())
        await tasks.wait()
        tasks.logExceptions()

        # log out of discord
        self.loggedIn = False
        await self.logout()
        # save bot save data
        self.saveAllDBs()
        # close the bot's aiohttp session
        await self.httpClient.close()
        print(datetime.now().strftime("%H:%M:%S: Shutdown complete."))


    @tasks.loop(seconds=cfg.shutdownCheckPeriodSeconds)
    async def shutdownCheckTask(self):
        if self.killer.kill_now:
            print("begin shutdown...")
            self.shutDownState = ShutDownState.shutdown
            await self.shutdown()


    @waitBeforeStartingTask
    @tasks.loop(**lib.timeUtil.td_secondsMinutesHours(cfg.timeouts.dataSaveFrequency))
    async def dbSaveTask(self):
        self.saveAllDBs()
        print(datetime.now().strftime("%H:%M:%S: Data saved!"))


    def dispatch(self, event_name, *args, **kwargs):
        if event_name == "ready" and not self.loggedIn:
            asyncio.create_task(self._asyncInit(True, *args, **kwargs))
        else:
            return super().dispatch(event_name, *args, **kwargs)

    
    async def _asyncInit(self, dispatchReady: bool = True, *args, **kwargs):
        if not self._schedulerLoaded:
            self.taskScheduler = timedTaskHeap.AutoCheckingTimedTaskHeap(asyncio.get_running_loop())
            self.taskScheduler.startTaskChecking()

        if not self.shutdownCheckTask.is_running():
            self.shutdownCheckTask.start()

        await self.reloadDBs()
        
        treeSyncTasks = lib.discordUtil.BasicScheduler()
        for g in cfg.developmentGuilds:
            treeSyncTasks.add(self.tree.sync(guild=g))
        if treeSyncTasks.any():
            await treeSyncTasks.wait()
            treeSyncTasks.raiseExceptions()

        self.loggedIn = True
        if dispatchReady:
            self.dispatch("ready", *args, **kwargs)


    @overload
    def getStaticComponentCallback(self, category: str, subCategory: str = None) -> "basedApp.CallBackType": ...

    @overload
    def getStaticComponentCallback(self, meta: Union[basedComponent.StaticComponentMeta, basedComponent.StaticComponentCallbackMeta]) -> "basedApp.CallBackType": ...

    def getStaticComponentCallback(self, val: Union[str, basedComponent.StaticComponentMeta, basedComponent.StaticComponentCallbackMeta], subCategory: str = None) -> "basedApp.CallBackType":
        if isinstance(val, (basedComponent.StaticComponentMeta, basedComponent.StaticComponentCallbackMeta)):
            key = basedComponent.staticComponentKey(val.category, val.subCategory)
        else:
            key = basedComponent.staticComponentKey(val, subCategory)
        return self.staticComponentCallbacks[key]


    @overload
    def hasStaticComponent(self, category: str, subCategory: str = None) -> bool: ...

    @overload
    def hasStaticComponent(self, meta: Union[basedComponent.StaticComponentMeta, basedComponent.StaticComponentCallbackMeta]) -> bool: ...

    def hasStaticComponent(self, val: Union[str, basedComponent.StaticComponentMeta, basedComponent.StaticComponentCallbackMeta], subCategory: str = None) -> bool:
        if isinstance(val, (basedComponent.StaticComponentMeta, basedComponent.StaticComponentCallbackMeta)):
            key = basedComponent.staticComponentKey(val.category, val.subCategory)
        else:
            key = basedComponent.staticComponentKey(val, subCategory)
        return key in self.staticComponentCallbacks
