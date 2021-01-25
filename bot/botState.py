from typing import TYPE_CHECKING
if TYPE_CHECKING:
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

usersDB: "UserDB" = None
guildsDB: "GuildDB" = None

logger: "Logger" = None

dbSaveTT: "TimedTask" = None

# Reaction Menus
reactionMenusDB: "ReactionMenuDB" = None
reactionMenusTTDB: "TimedTaskHeap" = None

shutdown: "ShutDownState" = ShutDownState.restart

updatesCheckTT: "TimedTask" = None
