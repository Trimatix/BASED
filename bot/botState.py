class ShutDownState:
    restart = 0
    shutdown = 1
    update = 2


client = None
httpClient = None
shutdown = ShutDownState.restart

usersDB = None
guildsDB = None
reactionMenusDB = None

dbSaveTT = None
updatesCheckTT = None

taskScheduler = None
logger = None
