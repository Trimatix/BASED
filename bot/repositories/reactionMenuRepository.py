from typing import Optional, Tuple, Type

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql._typing import _ColumnsClauseArgument
from sqlalchemy import select

from .snowflakeRepository import SnowflakeRepository
from ..reactionMenus import reactionMenu

class ReactionMenuRepository(SnowflakeRepository[reactionMenu.DatabaseReactionMenu]):
    def __init__(self, session: AsyncSession):
        super().__init__(reactionMenu.DatabaseReactionMenu, session)


    async def getMenuClassForRecord(self, recordId: int) -> Optional[Type[reactionMenu.DatabaseReactionMenu]]:
        """Get the menu class for the record with the given ID. Returns `None` if it does not exist.

        :param int recordId: integer discord ID for the DatabaseReactionMenu to get
        :return: The class for the stored record, or None if no record is found with the id
        :rtype: Optional[Type[DatabaseReactionMenu]]
        """
        recordTypeQuery = select(reactionMenu.DatabaseReactionMenu).where(reactionMenu.DatabaseReactionMenu.id == recordId).with_only_columns(reactionMenu.DatabaseReactionMenu.menuType)

        recordType = await self.session.scalar(recordTypeQuery)

        if recordType is None: return None
        return reactionMenu.databaseMenuClassFromName(recordType)


    async def get(self, recordId: int, withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[reactionMenu.DatabaseReactionMenu]]] = None) -> Optional[reactionMenu.DatabaseReactionMenu]:
        """Get the record with the given ID. Returns `None` if it does not exist.
        The menu is deserialized into the class named in its `menuType` field.

        :param int recordId: integer discord ID for the DatabaseReactionMenu to get
        :return: The stored record, or None if no record is found with the id
        :rtype: Optional[DatabaseReactionMenu]
        """
        menuClass = await self.getMenuClassForRecord(recordId)
        if menuClass is None: return None

        query = select(menuClass).where(menuClass.id == recordId)

        if withOnlyFields:
            query = query.with_only_columns(withOnlyFields)

        result = await self.session.execute(query)
        row = result.one_or_none()
        return None if row is None else row.t[0]
    

    async def getOrCreate(self, record: reactionMenu.DatabaseReactionMenu) -> reactionMenu.DatabaseReactionMenu:
        menuClass = await self.getMenuClassForRecord(record.id)
        if menuClass is None:
            await self.create(record)
            return record

        query = select(menuClass).where(menuClass.id == record.id)

        result = await self.session.execute(query)
    
        row = result.one()
        return row[0]
