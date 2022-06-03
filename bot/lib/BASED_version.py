import os
from ..cfg import cfg
from .. import lib
from datetime import datetime, timezone
import aiohttp
from carica import SerializableDataClass # type: ignore[import]
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from discord.utils import utcnow # type: ignore[import]

# Path to the BASED version json descriptor file. File also contains the timestamp of the next scheduled version check.
BASED_VERSIONFILE = str(Path(".BASED", "BASED_version.json"))

BASED_REPO_USER = "Trimatix"
BASED_REPO_NAME = "BASED"
# Pointer to the BASED repository. Do not change this.
BASED_REPO_URL = f"https://github.com/{BASED_REPO_USER}/{BASED_REPO_NAME}"
BASED_API_URL = f"https://api.github.com/repos/{BASED_REPO_USER}/{BASED_REPO_NAME}/releases"

@dataclass
class VersionInfo(SerializableDataClass):
    BASED_version: str # a version indicator from github
    next_update_check: float # a POSIX timestamp in UTC


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
    if utcnow() >= nextUpdateCheck:
        # Get latest version
        latest = await lib.github.getNewestTagOnRemote(httpClient, BASED_API_URL)

        # Schedule next updates check
        nextCheck = utcnow() + cfg.timeouts.BASED_updateCheckFrequency
        newVersion = VersionInfo(BASED_VERSION, nextCheck.timestamp())
        lib.jsonHandler.saveObject(BASED_VERSIONFILE, newVersion)

        # If no tags were found on remote, assume up to date.
        upToDate = (latest == BASED_VERSION) if latest else True
        return UpdateCheckResults(True, latestVersion=latest, upToDate=upToDate)

    # If not time to check yet, indicate as such
    return UpdateCheckResults(False, None, None)