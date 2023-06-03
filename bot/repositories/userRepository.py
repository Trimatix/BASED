from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from .snowflakeRepository import SnowflakeRepository
from ..users.basedUser import BasedUser

class UserRepository(SnowflakeRepository[BasedUser]):
    def __init__(self, session: AsyncSession):
        super().__init__(BasedUser, session)
