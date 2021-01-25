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

reactionMenusDB = None

shutdown = ShutDownState.restart

updatesCheckTT = None

taskScheduler = None
