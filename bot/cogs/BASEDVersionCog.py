from ..cfg import cfg
from .. import lib
from ..lib.BASED_version import checkForUpdates, BASED_REPO_URL
from .. import client

from discord.ext import commands, tasks # type: ignore[import]


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
    await bot.add_cog(BASED_VersionCog(bot), guilds=cfg.developmentGuilds) # type: ignore[reportGeneralTypeIssues]
