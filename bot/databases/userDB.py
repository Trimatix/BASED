from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine

from .snowflakeDb import SnowflakeDB
from ..users.basedUser import BasedUser

class UserDB(SnowflakeDB[BasedUser]):
    def __init__(self, engine: AsyncEngine):
        super().__init__(BasedUser, engine)
