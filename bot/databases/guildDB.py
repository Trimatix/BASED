from __future__ import annotations
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import select

from .snowflakeDb import SnowflakeDB
from ..users.basedGuild import BasedGuild
from ..lib.sql import SessionSharer

class GuildDB(SnowflakeDB[BasedGuild]):
    def __init__(self, engine: AsyncEngine):
        super().__init__(BasedGuild, engine)

    async def getCommandPrefix(self, recordId: int, session: Optional[AsyncSession] = None):
        query = select(BasedGuild).with_only_columns(BasedGuild.commandPrefix).where(BasedGuild.id == recordId)

        async with SessionSharer(session, self.sessionMaker) as s:
            return await s.session.scalar(query)
