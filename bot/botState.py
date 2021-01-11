class ShutDownState:
    restart = 0
    shutdown = 1
    update = 2


client = None

usersDB = None
guildsDB = None
reactionMenusDB = None

logger = None

dbSaveTT = None

# Reaction Menus
reactionMenusDB = None
reactionMenusTTDB = None

shutdown = ShutDownState.restart

updatesCheckTT = None
