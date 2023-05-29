from typing import List, cast
from tomlkit.items import Item

from ..lib.emojis import UninitializedBasedEmoji, BasedEmoji
from ..lib.discordUtil import SerializableDiscordObject
from .schema import BasicAccessLevelNames, EmojisConfig, SerializableTimedelta, TimeoutsConfig, PathsConfig, SerializablePath

# All emojis used by the bot
defaultEmojis = EmojisConfig(
    longProcess = cast(BasedEmoji, UninitializedBasedEmoji("⏳")),
    # When a user message prompts a DM to be sent, this emoji will be added to the message reactions.
    dmSent = cast(BasedEmoji, UninitializedBasedEmoji("📬")),
    cancel = cast(BasedEmoji, UninitializedBasedEmoji("🇽")),
    submit = cast(BasedEmoji, UninitializedBasedEmoji("✅")),
    spiral = cast(BasedEmoji, UninitializedBasedEmoji("🌀")),
    error = cast(BasedEmoji, UninitializedBasedEmoji("❓")),
    accept = cast(BasedEmoji, UninitializedBasedEmoji("👍")),
    reject = cast(BasedEmoji, UninitializedBasedEmoji("👎")),
    next = cast(BasedEmoji, UninitializedBasedEmoji('⏩')),
    previous = cast(BasedEmoji, UninitializedBasedEmoji('⏪')),
    numbers = cast(List[BasedEmoji], [UninitializedBasedEmoji("0️⃣"), UninitializedBasedEmoji("1️⃣"), UninitializedBasedEmoji("2️⃣"),
                UninitializedBasedEmoji("3️⃣"), UninitializedBasedEmoji("4️⃣"), UninitializedBasedEmoji("5️⃣"),
                UninitializedBasedEmoji("6️⃣"), UninitializedBasedEmoji("7️⃣"), UninitializedBasedEmoji("8️⃣"),
                UninitializedBasedEmoji("9️⃣"), UninitializedBasedEmoji("🔟")]),

    # The default emojis to list in a reaction menu
    menuOptions = cast(List[BasedEmoji], [UninitializedBasedEmoji("0️⃣"), UninitializedBasedEmoji("1️⃣"), UninitializedBasedEmoji("2️⃣"),
                    UninitializedBasedEmoji("3️⃣"), UninitializedBasedEmoji("4️⃣"), UninitializedBasedEmoji("5️⃣"),
                    UninitializedBasedEmoji("6️⃣"), UninitializedBasedEmoji("7️⃣"), UninitializedBasedEmoji("8️⃣"),
                    UninitializedBasedEmoji("9️⃣"), UninitializedBasedEmoji("🔟")])
)

timeouts = TimeoutsConfig(
    BASED_updateCheckFrequency = SerializableTimedelta(days=1),
    # The time to wait inbetween database autosaves.
    dataSaveFrequency = SerializableTimedelta(hours=1)
)

paths = PathsConfig(
    # path to folder to save log txts to
    logsFolder = SerializablePath("saveData", "logs")
)

basicAccessLevels = BasicAccessLevelNames(
    user = "user",
    serverAdmin = "admin",
    developer = "developer"
)

# Names of user access levels to be used in help menus.
# Also determines the number of access levels available, e.g when registering commands
userAccessLevels = [basicAccessLevels.user, "mod", basicAccessLevels.serverAdmin, basicAccessLevels.developer]

# Message to print alongside cmd_help menus
helpIntro = "Give a command name in `/help` for more detail."

# Name of the help section for un-categorized commands
defaultHelpSection = "Miscellaneous"

# Maximum number of commands each cmd_help menu may contain
maxCommandsPerHelpPage = 5

# List of module names from the commands package to import
includedCommandModules = ()

def cogPath(cogName: str, basePackage: str = "bot.cogs") -> str:
    return ".".join((basePackage, cogName))

includedCogs = (
    cogPath("BASEDVersionCog"),
    cogPath("CommonStaticComponentsCog"),
    cogPath("AdminMiscCog"),
    cogPath("HelpCog"),
    cogPath("DevMiscCog"),
    cogPath("UserMiscCog")
)

# Text to edit into expired menu messages
expiredMenuMsg = "😴 This role menu has now expired."

# The termination signal checking period.
shutdownCheckPeriodSeconds = 10

# Whether or not to check for updates to BASED
BASED_checkForUpdates = True

# Default prefix for commands
defaultCommandPrefix = "."

# discord user IDs of developers - will be granted developer command permissions
developers = [188618589102669826]

# IDs of 'development' servers, where commands will be synced to immediately, and dev commands will be enabled.
developmentGuilds = [SerializableDiscordObject(1)]

# Exactly one of botToken or botToken_envVarName must be given.
# botToken contains a string of your bot token
# botToken_envVarName contains the name of an environment variable to get your bot token from
botToken = ""
botToken_envVarName = ""

# The number of times to retry API calls when HTTP exceptions are thrown
httpErrRetries = 3

# The number of seconds to wait between API call retries upon HTTP exception catching
httpErrRetryDelaySeconds = 1

# Exactly one of databaseConnectionString or databaseConnectionString_envVarName must be given.
# databaseConnectionString directly contains the connection string for your database
# databaseConnectionString_envVarName contains the name of an environment variable to get your connection string from
databaseConnectionString = ""
databaseConnectionString_envVarName = ""


def validateConfig():
    global developmentGuilds
    if len(developmentGuilds) > 0 and isinstance(developmentGuilds[0], Item):
        developmentGuilds = [SerializableDiscordObject(int(i)) for i in developmentGuilds] # type: ignore[reportGeneralTypeIssues]
    for _, basicAccessLevel in basicAccessLevels._fieldItems():
        if basicAccessLevel not in userAccessLevels:
            raise ValueError(f"basic access level '{basicAccessLevel}' is missing from userAccessLevels")
