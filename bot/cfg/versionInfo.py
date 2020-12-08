import git
import os
from . import cfg
from .. import lib
from datetime import datetime
from typing import Dict, Union

# Path to the BASED version json descriptor file. File also contains the timestamp of the next scheduled version check.
BASED_VERSIONFILE = 'bot/cfg/version/BASED_version.json'
# Pointer to the BASED repository. Do not change this.
BASED_REPO_URL = "https://github.com/Trimatix/BASED.git"


class UpdateCheckResults:
    """Data class representing the results of a bot version check.

    :var updatesChecked: whether or not an updates check was attempted
    :vartype updatesChecked: bool
    :var latestVersion: String name of the latest version
    :vartype latestVersion: str
    :var upToDate: Whether or not the current bot version is latestVersion
    :vartype upToDate: bool
    """
    def __init__(self, updatesChecked : bool, latestVersion : str = None, upToDate : bool = None):
        """Data class representing the results of a bot version check.

        :param bool updatesChecked: whether or not an updates check was attempted
        :param str latestVersion: String name of the latest version. None when updatesChecked is False
        :param bool upToDate: Whether or not the current bot version is latestVersion. None when updatesChecked is False
        """
        self.updatesChecked = updatesChecked
        self.latestVersion = latestVersion
        self.upToDate = upToDate


def getBASEDVersion() -> Dict[str, Union[str, float]]:
    """Get info about the running BASED version, from file.

    :return: A dictionary describing the current BASED version, and the next scheduled updates check.
    :rtype: dict[string, string or float]
    """
    # Ensure file existence
    if not os.path.isfile(BASED_VERSIONFILE):
        raise RuntimeError("BASED version file not found, please update cfg.versionInfo.BASED_VERSIONFILE path")
    # Read version file
    return lib.jsonHandler.readJSON(BASED_VERSIONFILE)


def getNewestTagOnRemote(url : str) -> str:
    """Fetch the name of the latest tag on the given git remote.
    If the remote has no tags, empty string is returned.

    :param str url: URL to the git remote to check
    :return: String name of the the latest tag on the remote at URL, if the remote at URL has any tags. Empty string otherwise
    :rtype: str 
    """
    # Fetch latest tag. ls-remote --tags returns tags sorted by date, so select the first element.
    latest = git.cmd.Git().ls_remote("--tags", url).split("\n")[0]
    # Strip of the commit sha, and strip of leading tag identifiers ('refs/tags/') added by GitHub
    return latest[latest.rfind("/")+1:] if latest else ""


# Version of BASED currently installed
BASED_VERSION = getBASEDVersion()["BASED_version"]


def checkForUpdates() -> UpdateCheckResults:
    """Check the BASED repository for new releases.
    Could be easily extended to check your own bot repository for updates as well.

    :return: The latest BASED version and whether or not this installation is up to date, if the scheduled check time has been reached. UpdateCheckResults indicating that no check was performed otherwise.
    :rtype: UpdateCheckResults
    """
    # Fetch the next scheduled updates check from file
    nextUpdateCheck = datetime.utcfromtimestamp(getBASEDVersion()["next_update_check"])

    # Is it time to check yet?
    if datetime.utcnow() >= nextUpdateCheck:
        # Get latest version
        latest = getNewestTagOnRemote(BASED_REPO_URL)

        # Schedule next updates check
        nextCheck = datetime.utcnow() + lib.timeUtil.timeDeltaFromDict(cfg.BASED_updateCheckFrequency)
        lib.jsonHandler.writeJSON(BASED_VERSIONFILE,
                                    {   "BASED_version"     : BASED_VERSION,
                                        "next_update_check" : nextCheck.timestamp()})
        
        # If no tags were found on remote, assume up to date.
        upToDate = (latest == BASED_VERSION) if latest else True
        return UpdateCheckResults(True, latestVersion=latest, upToDate=upToDate)

    # If not time to check yet, indicate as such
    return UpdateCheckResults(False)
    
