from .bot import BasedClient
from .databases.userDB import UserDB
from .databases.guildDB import GuildDB
from .databases.reactionMenuDB import ReactionMenuDB
from .logging import Logger
from .scheduling.timedTask import TimedTask
from .scheduling.timedTaskHeap import TimedTaskHeap


class ShutDownState:
    restart = 0
    shutdown = 1
    update = 2


client: "BasedClient" = None
shutdown: ShutDownState = ShutDownState.restart

usersDB: "UserDB" = None
guildsDB: "GuildDB" = None
reactionMenusDB: "ReactionMenuDB" = None

dbSaveTT: "TimedTask" = None
updatesCheckTT: "TimedTask" = None

taskScheduler: "TimedTaskHeap" = None
logger: "Logger" = None
