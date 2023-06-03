from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .snowflakeRepository import SnowflakeRepository
from ..users.basedGuild import BasedGuild

class GuildRepository(SnowflakeRepository[BasedGuild]):
    def __init__(self, session: AsyncSession):
        super().__init__(BasedGuild, session)

    async def getCommandPrefix(self, recordId: int):
        query = select(BasedGuild).with_only_columns(BasedGuild.commandPrefix).where(BasedGuild.id == recordId)

        return await self.session.scalar(query)
