from typing import TYPE_CHECKING, cast
if TYPE_CHECKING:
    from .databases import userDB, guildDB, reactionMenuDB
    from .scheduling import timedTask, timedTaskHeap
    from . import logging
    from .client import BasedClient

class ShutDownState:
    restart = 0
    shutdown = 1
    update = 2


client = cast("BasedClient", None)
shutdown = ShutDownState.restart

usersDB = cast("userDB.UserDB", None)
guildsDB = cast("guildDB.GuildDB", None)
reactionMenusDB = cast("reactionMenuDB.ReactionMenuDB", None)

dbSaveTT = cast("timedTask.TimedTask", None)
updatesCheckTT = cast("timedTask.TimedTask", None)

taskScheduler = cast("timedTaskHeap.TimedTaskHeap", None)
logger = cast("logging.Logger", None)
