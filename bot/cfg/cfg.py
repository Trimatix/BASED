from ..lib.emojis import BasedEmoji, UninitializedBasedEmoji

longProcessEmoji = BasedEmoji(unicode="⏳")
userAccessLevels = ["user", "mod", "admin", "dev"]
helpIntro = "Here are my commands!"
maxCommandsPerHelpPage = 5

# List of module names from the ommands package to import
includedCommandModules = (  "usr_misc", "usr_deck",
                            "admn_misc",
                            "dev_misc")

helpEmbedTimeout = {"minutes": 3}

# When a user message prompts a DM to be sent, this emoji will be added to the message reactions.
dmSentEmoji = BasedEmoji(unicode="📬")

expiredMenuMsg = "😴 This role menu has now expired."

# The default emojis to list in a reaction menu
numberEmojis = [BasedEmoji(unicode="0️⃣"), BasedEmoji(unicode="1️⃣"), BasedEmoji(unicode="2️⃣"), BasedEmoji(unicode="3️⃣"), BasedEmoji(unicode="4️⃣"), BasedEmoji(unicode="5️⃣"), BasedEmoji(unicode="6️⃣"), BasedEmoji(unicode="7️⃣"), BasedEmoji(unicode="8️⃣"), BasedEmoji(unicode="9️⃣"), BasedEmoji(unicode="🔟")]
defaultMenuEmojis = numberEmojis
defaultCancelEmoji = BasedEmoji(unicode="🇽")
defaultSubmitEmoji = BasedEmoji(unicode="✅")
spiralEmoji = BasedEmoji(unicode="🌀")
defaultErrEmoji = BasedEmoji(unicode="❓")
defaultAcceptEmoji = BasedEmoji(unicode="👍")
defaultRejectEmoji = BasedEmoji(unicode="👎")
defaultNextEmoji = BasedEmoji(unicode='⏩')
defaultPreviousEmoji = BasedEmoji(unicode='⏪')

timedTaskCheckingType = "fixed"
timedTaskLatenessThresholdSeconds = 10

BASED_checkForUpdates = True
BASED_updateCheckFrequency = {"days": 1}

defaultCommandPrefix = "."

developers = [188618589102669826]

cardsPerHand = 7



##### SAVING #####

# The time to wait inbetween database autosaves.
savePeriod = {"hours":1}

# path to JSON files for database saves
userDBPath = "saveData/users.json"
guildDBPath = "saveData/guilds.json"
reactionMenusDBPath = "saveData/reactionMenus.json"

# path to folder to save log txts to
loggingFolderPath = "saveData/logs"

gameJoinMenuTimout = {"minutes": 5}

expansionPickerTimeout = {"minutes": 5}