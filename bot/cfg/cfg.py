from ..lib.emojis import UninitializedBasedEmoji

emojiVars = [   "longProcessEmoji",
                "loadingEmoji",
                "dmSentEmoji",
                "defaultCancelEmoji",
                "defaultSubmitEmoji",
                "spiralEmoji",
                "defaultErrEmoji",
                "defaultAcceptEmoji",
                "defaultRejectEmoji",
                "defaultNextEmoji",
                "defaultPreviousEmoji"
            ]

emojiListVars = [
                "numberEmojis",
                "defaultMenuEmojis"
                ]

pathVars =  [
                "baseSaveDataFolder",
                "userDBPath",
                "guildDBPath",
                "reactionMenusDBPath",
                "loggingFolderPath",
                "decksFolderPath",
                "deckMetaFolderPath",
                "cardFont",
                "googleAPICred"
            ]

longProcessEmoji = UninitializedBasedEmoji("⏳")
loadingEmoji = UninitializedBasedEmoji(793467306507763713)
userAccessLevels = ["user", "mod", "admin", "dev"]
helpIntro = "Here are my commands!"
maxCommandsPerHelpPage = 5

# List of module names from the commands package to import
includedCommandModules = (  "usr_misc", "usr_deck",
                            "admn_misc", "admin_deck",
                            "dev_misc")

helpEmbedTimeout = {"minutes": 3}

# When a user message prompts a DM to be sent, this emoji will be added to the message reactions.
dmSentEmoji = UninitializedBasedEmoji("📬")

expiredMenuMsg = "😴 This menu has now expired."

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

defaultCommandPrefix = "deck "

developers = [188618589102669826, 144137708711837696]

cardsPerHand = 7

emptyWhiteCard = "https://cdn.discordapp.com/attachments/793470493197729853/793470535039320084/emptyCard.png"
emptyBlackCard = emptyWhiteCard
submittedWhiteCard = emptyWhiteCard

# Number of seconds to wait inbetween each check for complete submissions
submissionWaitingPeriod = 10

submissionsReviewMenuTimeout = 1800

keepPlayingConfirmMenuTimeout = 600

roundsPickerTimeout = 300
roundsPickerOptions = [3, 5, 10, 15]



##### SAVING #####

# The time to wait inbetween database autosaves.
savePeriod = {"hours":1}

baseSaveDataFolder = "saveData"

# path to JSON files for database saves
userDBPath = baseSaveDataFolder + "/" + "users.json"
guildDBPath = baseSaveDataFolder + "/" + "guilds.json"
reactionMenusDBPath = baseSaveDataFolder + "/" + "reactionMenus.json"

# path to folder to save log txts to
loggingFolderPath = baseSaveDataFolder + "/" + "logs"

decksFolderPath = baseSaveDataFolder + "/" + "decks"
deckMetaFolderPath = baseSaveDataFolder + "/" + "deckMeta"

gameJoinMenuTimout = {"minutes": 5}

expansionPickerTimeout = {"minutes": 5}

cardFont = "bot" + "/" + "cardRenderer" + "/" + "HelveticaNeueLTStd-Bd.otf"
googleAPICred = "bot" + "/" + "cfg" + "/" + "google_client_secret.json"

cardsDCChannel = {"guild_id": 733652363235033088,
                    "channel_id": 796038447252766741}

defaultSDBRounds = 5

# Can be either "local" or "discord"
cardStorageMethod = "local"