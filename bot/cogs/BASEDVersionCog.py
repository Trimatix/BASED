import os
from ..cfg import cfg
from .. import lib
from .. import client
from datetime import datetime, timezone
import aiohttp
from carica import SerializableDataClass # type: ignore[import]
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from typing import List
import discord # type: ignore[import]
from discord.ext import commands, tasks # type: ignore[import]
from discord import app_commands # type: ignore[import]

@dataclass
class VersionInfo(SerializableDataClass):
    BASED_version: str # a version indicator from github
    next_update_check: float # a POSIX timestamp in UTC

# Path to the BASED version json descriptor file. File also contains the timestamp of the next scheduled version check.
BASED_VERSIONFILE = str(Path(".BASED", "BASED_version.json"))

BASED_REPO_USER = "Trimatix"
BASED_REPO_NAME = "BASED"
# Pointer to the BASED repository. Do not change this.
BASED_REPO_URL = f"https://github.com/{BASED_REPO_USER}/{BASED_REPO_NAME}"
BASED_API_URL = f"https://api.github.com/repos/{BASED_REPO_USER}/{BASED_REPO_NAME}/releases"


@dataclass
class UpdateCheckResults:
    """Data class representing the results of a bot version check.

    :var updatesChecked: whether or not an updates check was attempted
    :vartype updatesChecked: bool
    :var latestVersion: String name of the latest version. None when updatesChecked is False
    :vartype latestVersion: str
    :var upToDate: Whether or not the current bot version is latestVersion. None when updatesChecked is False
    :vartype upToDate: bool
    """
    updatesChecked: bool
    latestVersion: Optional[str]
    upToDate: Optional[bool]


def getBASEDVersion() -> VersionInfo:
    """Get info about the running BASED version, from file.

    :return: A dictionary describing the current BASED version, and the next scheduled updates check.
    :rtype: dict[string, string or float]
    """
    # Ensure file existence
    if not os.path.isfile(BASED_VERSIONFILE):
        raise RuntimeError("BASED version file not found, please update cfg.versionInfo.BASED_VERSIONFILE path")
    # Read version file
    return lib.jsonHandler.loadObject(BASED_VERSIONFILE, VersionInfo)


# Version of BASED currently installed
BASED_VERSION = getBASEDVersion().BASED_version


async def checkForUpdates(httpClient: aiohttp.ClientSession) -> UpdateCheckResults:
    """Check the BASED repository for new releases.
    Could be easily extended to check your own bot repository for updates as well.

    :param aiohttp.ClientSession httpClient: The ClientSession to request git info with
    :return: The latest BASED version and whether or not this installation is up to date, if the scheduled check time
             has been reached. UpdateCheckResults indicating that no check was performed otherwise.
    :rtype: UpdateCheckResults
    """
    # Fetch the next scheduled updates check from file
    nextUpdateCheck = datetime.fromtimestamp(getBASEDVersion().next_update_check, timezone.utc)

    # Is it time to check yet?
    if discord.utils.utcnow() >= nextUpdateCheck:
        # Get latest version
        latest = await lib.github.getNewestTagOnRemote(httpClient, BASED_API_URL)

        # Schedule next updates check
        nextCheck = discord.utils.utcnow() + cfg.timeouts.BASED_updateCheckFrequency
        newVersion = VersionInfo(BASED_VERSION, nextCheck.timestamp())
        lib.jsonHandler.saveObject(BASED_VERSIONFILE, newVersion)

        # If no tags were found on remote, assume up to date.
        upToDate = (latest == BASED_VERSION) if latest else True
        return UpdateCheckResults(True, latestVersion=latest, upToDate=upToDate)

    # If not time to check yet, indicate as such
    return UpdateCheckResults(False, None, None)


class BASED_VersionCog(commands.Cog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)
        bot.add_listener(self.on_ready)


    async def on_ready(self):
        if not self.bot.loggedIn:
            return
        self.BASED_updatesCheck.start()

    
    @tasks.loop(**lib.timeUtil.td_secondsMinutesHours(cfg.timeouts.BASED_updateCheckFrequency),
                reconnect=False)
    async def BASED_updatesCheck(self):
        try:
            BASED_versionCheck = await checkForUpdates(self.bot.httpClient)
        except lib.github.GithubError:
            print("⚠ BASED updates check failed. You may be checking for updates too quickly, the GitHub API may be down, " +
                    f"or your BASED updates checker version may be depracated: {BASED_REPO_URL}")
        else:
            if BASED_versionCheck.updatesChecked and not BASED_versionCheck.upToDate:
                print(f"⚠ New BASED update {BASED_versionCheck.latestVersion} now available! See " +
                    f"{BASED_REPO_URL} for instructions on how to update your BASED fork.")


async def setup(bot: client.BasedClient):
    await bot.add_cog(BASED_VersionCog(bot), guilds=cfg.developmentGuilds)
