from ..lib.emojis import UninitializedBasedEmoji

pathVars =  [
                "baseSaveDir",
                "userDBPath",
                "guildDBPath",
                "reactionMenusDBPath",
                "loggingFolderPath"
            ]

longProcessEmoji = UninitializedBasedEmoji("⏳")
userAccessLevels = ["user", "mod", "admin", "dev"]
helpIntro = "Here are my commands!"
maxCommandsPerHelpPage = 5

# List of module names from the ommands package to import
includedCommandModules = (  "usr_misc",
                            "admn_misc",
                            "dev_misc")

helpEmbedTimeout = {"minutes": 3}

# When a user message prompts a DM to be sent, this emoji will be added to the message reactions.
dmSentEmoji = UninitializedBasedEmoji("📬")

expiredMenuMsg = "😴 This role menu has now expired."

# The default emojis to list in a reaction menu
numberEmojis = [UninitializedBasedEmoji("0️⃣"), UninitializedBasedEmoji("1️⃣"), UninitializedBasedEmoji("2️⃣"), UninitializedBasedEmoji("3️⃣"), UninitializedBasedEmoji("4️⃣"), UninitializedBasedEmoji("5️⃣"), UninitializedBasedEmoji("6️⃣"), UninitializedBasedEmoji("7️⃣"), UninitializedBasedEmoji("8️⃣"), UninitializedBasedEmoji("9️⃣"), UninitializedBasedEmoji("🔟")]
defaultMenuEmojis = numberEmojis
defaultCancelEmoji = UninitializedBasedEmoji("🇽")
defaultSubmitEmoji = UninitializedBasedEmoji("✅")
spiralEmoji = UninitializedBasedEmoji("🌀")
defaultErrEmoji = UninitializedBasedEmoji("❓")
defaultAcceptEmoji = UninitializedBasedEmoji("👍")
defaultRejectEmoji = UninitializedBasedEmoji("👎")
defaultNextEmoji = UninitializedBasedEmoji('⏩')
defaultPreviousEmoji = UninitializedBasedEmoji('⏪')

timedTaskCheckingType = "fixed"
timedTaskLatenessThresholdSeconds = 10

BASED_checkForUpdates = True
BASED_updateCheckFrequency = {"days": 1}

defaultCommandPrefix = "."

developers = [188618589102669826]



##### SAVING #####

# The time to wait inbetween database autosaves.
savePeriod = {"hours":1}

# path to JSON files for database saves
baseSaveDir = "saveData"
userDBPath = baseSaveDir + "/" + "users.json"
guildDBPath = baseSaveDir + "/" + "guilds.json"
reactionMenusDBPath = baseSaveDir + "/" + "reactionMenus.json"

# path to folder to save log txts to
loggingFolderPath = baseSaveDir + "/" + "logs"

botToken = ""
botToken_envVarName = ""