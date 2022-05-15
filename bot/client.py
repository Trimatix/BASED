import asyncio
import signal
from typing import Optional, Dict, Tuple, Union, overload
import aiohttp
import discord # type: ignore[import]
from discord.ext.commands import Bot as ClientBaseClass # type: ignore[import]
from discord.ext import tasks # type: ignore[import]
from datetime import datetime, timedelta
from .databases import userDB, guildDB, reactionMenuDB
import os
from . import lib
from .cfg import cfg
from . import logging
from .scheduling import timedTaskHeap
from .interactions import basedCommand, accessLevel, basedComponent, basedApp


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
        self.staticComponentCallbacks: Dict[Tuple[str, str], basedApp.CallBackType] = {}


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
            return
        elif event_name == "interaction":
            interaction: discord.Interaction = args[0]
            if interaction.type == discord.InteractionType.component and basedComponent.customIdIsStaticComponent(interaction.data["custom_id"]):
                meta = basedComponent.staticComponentMeta(interaction.data["custom_id"])
                if self.hasStaticComponent(meta):
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
                    args = args + (meta.args,)
                    asyncio.create_task(component(*args, **kwargs))
                    return
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
