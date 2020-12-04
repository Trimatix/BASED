from github import Github
import os
from . import cfg
from .. import lib
from datetime import datetime

NEXT_UPDATE_CHECK_FILE = 'BASED_nextUpdateCheck.json'
BASED_VERSION = "v0.1-alpha"

class UpdateCheckResults:
    def __init__(self, updatesChecked : bool, latestVersion : str = None, upToDate : bool = None):
        self.updatesChecked = updatesChecked
        self.latestVersion = latestVersion
        self.upToDate = upToDate


def checkForUpdates():
    timeToCheck = True
    if os.path.isfile(NEXT_UPDATE_CHECK_FILE):
        nextUpdateCheck = datetime.utcfromtimestamp(lib.jsonHandler.readJSON(NEXT_UPDATE_CHECK_FILE)["timestamp"])
        if datetime.utcnow() < nextUpdateCheck:
            timeToCheck = False

    if timeToCheck:

        g = Github(os.environ["BASED_GH_TOKEN"])
        repo = g.get_repo("Trimatix/BASED")
        BASED_tags = repo.get_tags()

        try:
            latestVer = BASED_tags[0].name
        except IndexError:
            latestVer = BASED_VERSION

        lib.jsonHandler.writeJSON(NEXT_UPDATE_CHECK_FILE, {"timestamp": (datetime.utcnow() + lib.timeUtil.timeDeltaFromDict(cfg.BASED_updateCheckFrequency)).timestamp()})

        return UpdateCheckResults(True, latestVersion=latestVer, upToDate=latestVer == BASED_VERSION)    
    return UpdateCheckResults(False)
    
