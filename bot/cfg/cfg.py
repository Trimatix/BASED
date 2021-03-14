from ..lib.emojis import UninitializedBasedEmoji

# All emojis used by the bot
defaultEmojis = {
    "longProcess": UninitializedBasedEmoji("⏳"),
    "loading": UninitializedBasedEmoji(793467306507763713),
    # When a user message prompts a DM to be sent, this emoji will be added to the message reactions.
    "dmSent": UninitializedBasedEmoji("📬"),
    "cancel": UninitializedBasedEmoji("🇽"),
    "submit": UninitializedBasedEmoji("✅"),
    "spiral": UninitializedBasedEmoji("🌀"),
    "error": UninitializedBasedEmoji("❓"),
    "accept": UninitializedBasedEmoji("👍"),
    "reject": UninitializedBasedEmoji("👎"),
    "next": UninitializedBasedEmoji('⏩'),
    "previous": UninitializedBasedEmoji('⏪'),
    "numbers": [UninitializedBasedEmoji("0️⃣"), UninitializedBasedEmoji("1️⃣"), UninitializedBasedEmoji("2️⃣"),
                UninitializedBasedEmoji("3️⃣"), UninitializedBasedEmoji("4️⃣"), UninitializedBasedEmoji("5️⃣"),
                UninitializedBasedEmoji("6️⃣"), UninitializedBasedEmoji("7️⃣"), UninitializedBasedEmoji("8️⃣"),
                UninitializedBasedEmoji("9️⃣"), UninitializedBasedEmoji("🔟")],

    # The default emojis to list in a reaction menu
    "menuOptions": [UninitializedBasedEmoji("0️⃣"), UninitializedBasedEmoji("1️⃣"), UninitializedBasedEmoji("2️⃣"),
                    UninitializedBasedEmoji("3️⃣"), UninitializedBasedEmoji("4️⃣"), UninitializedBasedEmoji("5️⃣"),
                    UninitializedBasedEmoji("6️⃣"), UninitializedBasedEmoji("7️⃣"), UninitializedBasedEmoji("8️⃣"),
                    UninitializedBasedEmoji("9️⃣"), UninitializedBasedEmoji("🔟")]
}

timeouts = {
    "helpMenu": {"minutes": 3},
    "BASED_updateCheckFrequency": {"days": 1},
    # The time to wait inbetween database autosaves.
    "dataSaveFrequency": {"hours":1},
    # Number of seconds to wait inbetween each check for complete submissions
    "allSubmittedCheckPeriodSeconds": 10,
    # Number of seconds to wait before timing out the SDB round submissions review menu
    "submissionsReviewMenuSeconds": 1800,
    # Number of seconds to wait before timing out the SDB 'keep playing?' confirmation menu
    "keepPlayingMenuSeconds": 600,
    # Number of seconds to wait before timing out the SDB number of rounds picker
    "numRoundsPickerSeconds": 300,
    # The time that the SDB 'join game' menu should be active for, before auto starting the game
    "gameJoinMenu": {"minutes": 5},
    # The time that the SDB expansions picker menu should be active for when stating a new game
    "expansionsPicker": {"minutes": 5},
    # The time allowed to pick a new deck master when relinquishing game ownership
    "sdbPlayerSelectorSeconds": 300,
    # The time to wait for a new deck name message in cmd_rename
    "deckRenameSeconds": 180
}

paths = {
    # path to JSON files for database saves
    "usersDB": "saveData" + "/" + "users.json",
    "guildsDB": "saveData" + "/" + "guilds.json",
    "reactionMenusDB": "saveData" + "/" + "reactionMenus.json",

    # path to folder to save log txts to
    "logsFolder": "saveData" + "/" + "logs",

    # Root folder to save SDB card images into. May be deleted again depending on cardStorageMethod
    "decksFolder": "saveData" + "/" + "decks",
    #  Folder to store SDB deck meta json files in
    "deckMetaFolder": "saveData" + "/" + "deckMeta",
    # Font to render cards with
    "cardFont": "bot" + "/" + "cardRenderer" + "/" + "HelveticaNeueLTStd-Bd.otf",
    # Google API credentials to use when reading spreadsheets
    "googleAPICred": "bot" + "/" + "cfg" + "/" + "google_client_secret.json",
    
    # Working folder for temporary image files
    "cardsTemp": "saveData" + "/" + "decks" + "/" + "temp"
}

# Names of user access levels to be used in help menus.
# Also determines the number of access levels available, e.g when registering commands
userAccessLevels = ["user", "mod", "admin", "dev"]

# Message to print alongside cmd_help menus
helpIntro = "Here are my commands!"

# Maximum number of commands each cmd_help menu may contain
maxCommandsPerHelpPage = 5

# List of module names from the commands package to import
includedCommandModules = (  "usr_misc", "usr_deck", "usr_dm",
                            "admn_misc", "admin_deck",
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
defaultCommandPrefix = "deck "

# discord user IDs of developers - will be granted developer command permissions
developers = [188618589102669826, 144137708711837696]

# Number of cards to distribute to each player per round
cardsPerHand = 7

# Fall back image for the backs of cards in case none are included in the deck
emptyWhiteCard = "https://cdn.discordapp.com/attachments/793470493197729853/793470535039320084/emptyCard.png"
emptyBlackCard = emptyWhiteCard
submittedWhiteCard = emptyWhiteCard

# Options for the SDB number of rounds to play picker (not including free play)
roundsPickerOptions = [3, 5, 10, 15]
# Default number of rounds to play. Only used if an error was encountered with the rounds picker reaction menu.
defaultSDBRounds = 5

# Discord channel to store card images in. Only used when cardStorageMethod is "discord"
cardsDCChannel = {"guild_id": 733652363235033088,
                    "channel_id": 796038447252766741}

# Can be either "local" or "discord"
cardStorageMethod = "local"

# Exactly one of botToken or botToken_envVarName must be given.
# botToken contains a string of your bot token
# botToken_envVarName contains the name of an environment variable to get your bot token from
botToken = ""
botToken_envVarName = "SDB_BOT_TOKEN"

# Can be either "sequential" or "merged"
submissionsPresentationMethod = "merged"
# Number of cards to display per line on an merged image of all of a player's submitted cards
mergedSubmissionsMenu_lineLength = 3

# Font size of main text to render on cards
cardContentFontSize = 90
# Font size of smaller text to render on cards
cardTitleFontSize = 40

# Default number of options to present in a PagedReactionMenu
defaultOptionsPerPage = 5

# Minimum number of players required to start a game
minPlayerCount = 2

# The maximum number of characters a deck name may consist of
maxDeckNameLength = 30
