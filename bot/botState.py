from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from .client import BasedClient

class ShutDownState:
    restart = 0
    shutdown = 1
    update = 2


client = cast("BasedClient", None)
