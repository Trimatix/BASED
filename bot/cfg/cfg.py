from ..lib.emojis import UninitializedBasedEmoji
from ..lib.discordUtil import SerializableDiscordObject
from .schema import EmojisConfig, SerializableTimedelta, TimeoutsConfig, PathsConfig, SerializablePath

# All emojis used by the bot
defaultEmojis = EmojisConfig(
    longProcess = UninitializedBasedEmoji("⏳"),
    # When a user message prompts a DM to be sent, this emoji will be added to the message reactions.
    dmSent = UninitializedBasedEmoji("📬"),
    cancel = UninitializedBasedEmoji("🇽"),
    submit = UninitializedBasedEmoji("✅"),
    spiral = UninitializedBasedEmoji("🌀"),
    error = UninitializedBasedEmoji("❓"),
    accept = UninitializedBasedEmoji("👍"),
    reject = UninitializedBasedEmoji("👎"),
    next = UninitializedBasedEmoji('⏩'),
    previous = UninitializedBasedEmoji('⏪'),
    numbers = [UninitializedBasedEmoji("0️⃣"), UninitializedBasedEmoji("1️⃣"), UninitializedBasedEmoji("2️⃣"),
                UninitializedBasedEmoji("3️⃣"), UninitializedBasedEmoji("4️⃣"), UninitializedBasedEmoji("5️⃣"),
                UninitializedBasedEmoji("6️⃣"), UninitializedBasedEmoji("7️⃣"), UninitializedBasedEmoji("8️⃣"),
                UninitializedBasedEmoji("9️⃣"), UninitializedBasedEmoji("🔟")],

    # The default emojis to list in a reaction menu
    menuOptions = [UninitializedBasedEmoji("0️⃣"), UninitializedBasedEmoji("1️⃣"), UninitializedBasedEmoji("2️⃣"),
                    UninitializedBasedEmoji("3️⃣"), UninitializedBasedEmoji("4️⃣"), UninitializedBasedEmoji("5️⃣"),
                    UninitializedBasedEmoji("6️⃣"), UninitializedBasedEmoji("7️⃣"), UninitializedBasedEmoji("8️⃣"),
                    UninitializedBasedEmoji("9️⃣"), UninitializedBasedEmoji("🔟")]
)

timeouts = TimeoutsConfig(
    helpMenu = SerializableTimedelta(minutes=3),
    BASED_updateCheckFrequency = SerializableTimedelta(days=1),
    # The time to wait inbetween database autosaves.
    dataSaveFrequency = SerializableTimedelta(hours=1)
)

paths = PathsConfig(
    # path to JSON files for database saves
    usersDB = SerializablePath("saveData", "users.json"),
    guildsDB = SerializablePath("saveData", "guilds.json"),
    reactionMenusDB = SerializablePath("saveData", "reactionMenus.json"),

    # path to folder to save log txts to
    logsFolder = SerializablePath("saveData", "logs"),
    # path to file to save BASED version to
    BASED_versionFile = SerializablePath(".BASED", "BASED_version.json")
)

# Names of user access levels to be used in help menus.
# Also determines the number of access levels available, e.g when registering commands
userAccessLevels = ["user", "mod", "admin", "dev"]

# Message to print alongside cmd_help menus
helpIntro = "Here are my commands!"

# Maximum number of commands each cmd_help menu may contain
maxCommandsPerHelpPage = 5

# List of module names from the commands package to import
includedCommandModules = ("usr_misc",
                          "admn_misc",
                          "dev_misc")

# Text to edit into expired menu messages
expiredMenuMsg = "😴 This role menu has now expired."

# Use "fixed" to check for task expiry every timedTaskLatenessThresholdSeconds (polling-based scheduler)
# Use "dynamic" to check for task expiry exactly at the time of task expiry (interrupts-based scheduler)
timedTaskCheckingType = "dynamic"
# Number of seconds by with the expiry of a timedtask may acceptably be late.
# Regardless of timedTaskCheckingType, this is used for the termination signal checking period.
timedTaskLatenessThresholdSeconds = 10

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
