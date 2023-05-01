import asyncio
from inspect import iscoroutinefunction
import signal
from typing import List, Optional, Dict, Tuple, Type, Union, cast, overload
from pathlib import Path
import aiohttp
import discord # type: ignore[import]
from discord import app_commands
from discord.ext.commands import Bot as ClientBaseClass # type: ignore[import]
from discord.ext import tasks # type: ignore[import]
from discord.utils import MISSING # type: ignore[import]
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from .interactions import accessLevels, commandChecks
from .databases import userDB, guildDB, reactionMenuDB
import os
from . import lib
from .cfg import cfg
from . import logging
from .scheduling import timedTaskHeap
from .interactions import basedCommand, basedComponent, basedApp
from .reactionMenus import reactionMenu


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


def waitBeforeStartingTask(task: tasks.Loop):
    async def inner():
        await asyncio.sleep(timedelta(seconds=task.seconds or 0, minutes=task.minutes or 0, hours=task.hours or 0).total_seconds())
    
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

    def __init__(self, databaseEngine: AsyncEngine,
                        usersDB: Optional[userDB.UserDB] = None,
                        guildsDB: Optional[guildDB.GuildDB] = None,
                        inMemoryReactionMenusDB: Optional[Dict[int, "reactionMenu.InMemoryReactionMenu"]] = None,
                        databaseReactionMenusDB: Optional[reactionMenuDB.ReactionMenuDB] = None,
                        logger: Optional[logging.Logger] = None,
                        httpClient: Optional[aiohttp.ClientSession] = None):
        
        self.databaseEngine = databaseEngine
        self.sessionMaker = async_sessionmaker(self.databaseEngine)

        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="‎", intents=intents)

        self._usersDB = usersDB
        self._guildsDB = guildsDB
        self._databaseReactionMenusDB = databaseReactionMenusDB
        self._inMemoryReactionMenusDB = inMemoryReactionMenusDB
        self._dbsLoaded = None not in (usersDB, guildsDB, databaseReactionMenusDB, inMemoryReactionMenusDB)

        self.loggedIn = False
        self.launchTime = discord.utils.utcnow()
        self.killer = GracefulKiller()

        self._taskScheduler = None
        self._schedulerLoaded = False
        self.shutDownState = ShutDownState.restart
        
        self.logger = logger if logger is not None else logging.Logger()
        self._httpClient = httpClient

        self.basedCommands: Dict[discord.app_commands.Command, "basedCommand.BasedCommandMeta"] = {}
        self.staticComponentCallbacks: Dict["basedComponent.StaticComponents", "basedComponent.StaticComponentCallbackMeta"] = {}

        self.helpSections: Dict[str, List[discord.app_commands.Command]] = {}

        self.add_listener(self.on_interaction)


    async def on_interaction(self, interaction: discord.Interaction):
        customId = None if interaction.data is None else interaction.data.get("custom_id", None)
        if interaction.type != discord.InteractionType.component \
                or customId is None \
                or not basedComponent.customIdIsStaticComponent(customId):
            return
        componentMeta = basedComponent.staticComponentMeta(customId)
        if not self.hasStaticComponent(componentMeta.ID):
            return
        
        callbackMeta = self.getStaticComponentCallbackMeta(componentMeta.ID)
        cbArgs = (interaction, componentMeta.args) if callbackMeta.takesArgs else (interaction,)

        # Pass the owning object (e.g self/cls) to the callback if it needs one
        if basedApp.isCogApp(callbackMeta.callback):
            cogName = basedApp.getCogAppCogName(callbackMeta.callback)
            cog = self.get_cog(cogName)
            if cog is None:
                raise ValueError(f"unable to find cog '{cogName}' for static component: {callbackMeta.callback.__qualname__}")

        # Ignoring some warnings here for incorrect call syntax - pyright can't see that the tuple will always contain
        # the correct arguments, because we can't unpack a tuple until runtime
            await callbackMeta.callback(cog, *cbArgs) # type: ignore[reportGeneralTypeIssues]
        elif callbackMeta.hasSelf():
            await callbackMeta.callback(callbackMeta.cbSelf, *cbArgs) # type: ignore[reportGeneralTypeIssues]
        else:
            await callbackMeta.callback(*cbArgs) # type: ignore[reportGeneralTypeIssues]


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
        if meta.helpSection not in self.helpSections:
            self.helpSections[meta.helpSection] = [command]
        elif len(self.helpSections) == 99:
            raise ValueError("Maximum help sections exceeded. Only 99 help sections are supported.")
        else:
            self.helpSections[meta.helpSection].append(command)
        self.basedCommands[command] = meta


    def addStaticComponent(self, callback: "basedComponent.StaticComponentCallbackType"):
        """Register a static component callback's metadata with the bot.
        This enables static component behaviour as described by the `staticComponentCallback` decorator.

        :param callback: The static component to register
        :type command: basedComponent.StaticComponentCallbackType
        :raises KeyError: If the component is already registered
        :raises ValueError: If the callback has not been made into a static component callback with the `staticComponentCallback` decorator
        """
        if basedApp.appType(callback) != basedApp.BasedAppType.StaticComponent:
            raise ValueError(f"callback {callback.__qualname__} is not a static component callback")
        
        meta = basedComponent.staticComponentCallbackMeta(callback)
        if meta.ID in self.staticComponentCallbacks:
            raise KeyError(f"Static component callback {callback.__qualname__} is already registered")

        self.staticComponentCallbacks[meta.ID] = meta


    def basedCommand(self,
        *,
        accessLevel: Union[Type["accessLevels.AccessLevel"], str] = MISSING,
        showInHelp: bool = True,
        helpSection: Optional[str] = None,
        formattedDesc: Optional[str] = None,
        formattedParamDescs : Optional[Dict[str, str]] = None
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

            if helpSection is not None:
                basedCommand.validateHelpSection(helpSection)

            basedApp.basedApp(func.callback, basedApp.BasedAppType.AppCommand)
            setattr(func.callback, "__based_command_meta__", basedCommand.BasedCommandMeta(accessLevel, showInHelp, helpSection, formattedDesc, formattedParamDescs))
            self.addBasedCommand(func)

            if accessLevel is not MISSING:
                func.add_check(commandChecks.requireAccess(accessLevel))

            return func

        return decorator


    def staticComponentCallback(self, ID: "basedComponent.StaticComponents"):
        """Decorator marking a coroutine as a static component callback.
        The callback for static components identifying this callback by ID will be preserved across bot restarts

        Example usage:
        ```
        @bot.staticComponentCallback(StaticComponents.myCallback)
        async def myCallback(interaction: Interaction, args: str):
            await interaction.response.send_message(f"This static callback received args: {args}")

        @bot.app_commands.command(name="send-static-menu")
        async def sendStaticMenu(interaction: Interaction):
            staticButton = Button(label="send callback")
            staticButton = StaticComponents.myCallback(staticButton, args="hello")
            view.add_item(staticButton)
            await interaction.response.send_message(view=view)
        ```
        If the `send-static-menu` app command is sent, then a message will be sent in return with a button to trigger `myCallback`.
        Clicking this button will send another message with the content "hello".
        If the bot is restarted, then the button will still work.
        This works by attaching a known `custom_id` to the button, containing the static component ID and args.

        :var ID: The ID of the static component in the `StaticComponents` enum
        :type ID: StaticComponents
        """
        def decorator(func, ID=ID):
            if not iscoroutinefunction(func):
                raise TypeError("Decorator can only be applied to coroutines")

            cbSelf = basedComponent.validateStaticComponentCallbackSelf(func)
            basedApp.basedApp(func, basedApp.BasedAppType.StaticComponent)
            setattr(func, "__static_component_meta__", basedComponent.StaticComponentCallbackMeta(func, ID, cbSelf))
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


    @overload
    def removeStaticComponent(self, callback: "basedComponent.StaticComponentCallbackType"):
        """Un-register a static component callback's metadata with the bot.
        This disables static component behaviour as described by the `staticComponentCallback` decorator.

        :param callback: The static component to un-register
        :type command: basedComponent.StaticComponentCallbackType
        :raises KeyError: If the component is not registered
        :raises ValueError: If the callback has not been made into a static component callback with the `staticComponentCallback` decorator
        """

    @overload
    def removeStaticComponent(self, ID: "basedComponent.StaticComponents"):
        """Un-register a static component callback's metadata with the bot.
        This disables static component behaviour as described by the `staticComponentCallback` decorator.

        :param ID: The ID of the component in the `StaticComponents` enum
        :type ID: basedComponent.StaticComponents
        :raises KeyError: If the component is not registered
        :raises ValueError: If the callback has not been made into a static component callback with the `staticComponentCallback` decorator
        """

    # ignoring a warning here bceause the two overloads for this method correctly use different names for their parameters
    def removeStaticComponent(self, val: Union["basedComponent.StaticComponentCallbackType", "basedComponent.StaticComponents"]): # type: ignore[reportGeneralTypeIssues]
        if not isinstance(val, basedComponent.StaticComponents):
            if basedApp.appType(val) != basedApp.BasedAppType.StaticComponent:
                raise ValueError(f"callback {val.__qualname__} is not a static component callback")
        
            meta = basedComponent.staticComponentCallbackMeta(val)
            ID = meta.ID
        else:
            ID = val

        if ID not in self.staticComponentCallbacks:
            raise KeyError(f"Static component callback {ID.name} is not registered")
        
        del self.staticComponentCallbacks[ID]


    def commandsInSectionForAccessLevel(self, section: str, level: "accessLevels.AccessLevelType") -> List[discord.app_commands.Command]:
        """Get the commands in help section `section` that require access level `level`

        :param section: The help section for commands to look up
        :type section: str
        :param level: The access level that commands should require
        :type level: accessLevels.AccessLevelType
        :return: A list of commands in help section `section` requiring access level `level`
        :rtype: List[discord.app_commands.Command]
        """
        return [c for c in self.helpSections[section] if basedCommand.accessLevel(c) is level and basedCommand.commandMeta(c).showInHelp]


    def helpSectionsForAccessLevel(self, level: "accessLevels.AccessLevelType") -> Dict[str, List[discord.app_commands.Command]]:
        """Get the commands for a particular access level, organized by help section

        :param level: The access level of commands to look up
        :type level: accessLevels.AccessLevelType
        :return: The commands that require `level`, organized by help section
        :rtype: Dict[str, List[discord.app_commands.Command]]
        """
        result = {section: self.commandsInSectionForAccessLevel(section, level) for section in self.helpSections}
        return {s: c for s, c in result.items() if c}


    @property
    def httpClient(self) -> aiohttp.ClientSession:
        if self._httpClient is None:
            raise lib.exceptions.NotReady("httpClient not yet loaded. BasedClient.httpClient is only available after on_ready.")
        return self._httpClient


    async def setup_hook(self):
        if self._httpClient is None:
            self._httpClient = aiohttp.ClientSession()

    
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
        return cast(userDB.UserDB, self._usersDB)


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
        return cast(guildDB.GuildDB, self._guildsDB)


    @property
    def databaseReactionMenusDB(self):
        """The bot's database of reaction menus.
        Databases are only available after on_ready.

        :raises lib.exceptions.NotReady: Databases not loaded yet
        :return: The bot's database of user metadata.
        :rtype: databases.reactionMenuDB.ReactionMenuDB
        """
        if not self._dbsLoaded:
            raise lib.exceptions.NotReady("Databases not yet loaded. BasedClient._databaseReactionMenusDB is only available after on_ready.")
        return cast(reactionMenuDB.ReactionMenuDB, self._databaseReactionMenusDB)
    

    @property
    def inMemoryReactionMenusDB(self):
        """The bot's database of reaction menus.
        Databases are only available after on_ready.

        :raises lib.exceptions.NotReady: Databases not loaded yet
        :return: The bot's database of user metadata.
        :rtype: databases.reactionMenuDB.ReactionMenuDB
        """
        if not self._dbsLoaded:
            raise lib.exceptions.NotReady("Databases not yet loaded. BasedClient.inMemoryReactionMenusDB is only available after on_ready.")
        return cast(Dict[int, reactionMenu.InMemoryReactionMenu], self._inMemoryReactionMenusDB)


    @property
    def taskScheduler(self):
        """The bot's running task scheduler
        Only available after on_ready.

        :raises lib.exceptions.NotReady: scheduler not loaded yet
        :return: The bot's task scheduler.
        :rtype: TimedTaskHeap
        """
        if not self._schedulerLoaded:
            raise lib.exceptions.NotReady("Task scheduler not yet loaded. BasedClient.taskScheduler is only available after on_ready.")
        return cast(timedTaskHeap.AutoCheckingTimedTaskHeap, self._taskScheduler)


    async def reloadDBs(self):
        """Save all savedata to file, and start the db saving task if it is not running.
        inMemoryReactionMenusDB is not affected.
        """
        self._usersDB = userDB.UserDB(self.databaseEngine)
        self._guildsDB = guildDB.GuildDB(self.databaseEngine)
        self._databaseReactionMenusDB = reactionMenuDB.ReactionMenuDB(self.databaseEngine)
        if self._inMemoryReactionMenusDB is None:
            self._inMemoryReactionMenusDB = {}
        
        async with self.sessionMaker() as session:
            print(f"{await self._usersDB.countAllDocuments(session=session)} users loaded")                    
            print(f"{await self._guildsDB.countAllDocuments(session=session)} guilds loaded")                  
            print(f"{await self._databaseReactionMenusDB.countAllDocuments(session=session)} database reaction menus loaded")

        print(f"{len(self._inMemoryReactionMenusDB)} in memory reaction menus loaded")
        
        self._dbsLoaded = True

        if not self.dbSaveTask.is_running():
            self.dbSaveTask.start()


    def saveAllDBs(self):
        """Save all of the bot's savedata to file.
        This currently only save logs.
        """
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
        for menu in self.inMemoryReactionMenusDB.values():
            tasks.add(menu.end(self, timedOut=True))

        await tasks.wait()
        tasks.logExceptions()

        # log out of discord
        self.loggedIn = False
        await self.close()
        # save bot save data
        self.saveAllDBs()
        # close the bot's aiohttp session
        await self.httpClient.close()
        await self.databaseEngine.dispose()

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
            self._taskScheduler = timedTaskHeap.AutoCheckingTimedTaskHeap(asyncio.get_running_loop())
            self._taskScheduler.startTaskChecking()

        if not self.shutdownCheckTask.is_running():
            self.shutdownCheckTask.start()

        await self.reloadDBs()

        self.loggedIn = True
        if dispatchReady:
            self.dispatch("ready", *args, **kwargs)


    def getStaticComponentCallbackMeta(self, ID: "basedComponent.StaticComponents") -> "basedComponent.StaticComponentCallbackMeta":
        """Look up a registered static component callback by ID

        :param ID: The ID of the component in the `StaticComponents` enum
        :type ID: basedComponent.StaticComponents
        :return: The metadata recorded about the callback that is registered with id `ID`
        :rtype: basedComponent.StaticComponentCallbackMeta
        """
        return self.staticComponentCallbacks[ID]


    def getStaticComponentCallback(self, ID: "basedComponent.StaticComponents") -> "basedComponent.StaticComponentCallbackType":
        """Look up a registered static component callback by ID

        :param ID: The ID of the component in the `StaticComponents` enum
        :type ID: basedComponent.StaticComponents
        :return: The callback that is registered with id `ID`. This may or may not belong to a Cog
        :rtype: basedComponent.StaticComponentCallbackType
        """
        return self.getStaticComponentCallbackMeta(ID).callback


    def hasStaticComponent(self, ID: "basedComponent.StaticComponents") -> bool:
        """Decide whether the client has a static component callback registered, whether in a loaded Cog or not.
        Does not consider unloaded Cogs

        :param ID: The ID of the component in the `StaticComponents` enum
        :type ID: basedComponent.StaticComponents
        :return: `True` if a static component is registered with id `ID`, `False` otherwise
        :rtype: bool
        """
        return ID in self.staticComponentCallbacks
