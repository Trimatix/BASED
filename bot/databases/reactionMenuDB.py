from typing import Optional, Tuple, Type
from ..reactionMenus import reactionMenu

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.sql._typing import _ColumnsClauseArgument
from sqlalchemy import select

from .snowflakeDb import SnowflakeDB

class ReactionMenuDB(SnowflakeDB[reactionMenu.DatabaseReactionMenu]):
    def __init__(self, engine: AsyncEngine):
        super().__init__(reactionMenu.DatabaseReactionMenu, engine)


    async def getMenuClassForRecord(self, recordId: int, session: Optional[AsyncSession] = None) -> Optional[Type[reactionMenu.DatabaseReactionMenu]]:
        """Get the menu class for the record with the given ID. Returns `None` if it does not exist.

        :param int recordId: integer discord ID for the DatabaseReactionMenu to get
        :return: The class for the stored record, or None if no record is found with the id
        :rtype: Optional[Type[DatabaseReactionMenu]]
        """
        recordTypeQuery = select(reactionMenu.DatabaseReactionMenu).where(reactionMenu.DatabaseReactionMenu.id == recordId).with_only_columns(reactionMenu.DatabaseReactionMenu.menuType)

        async with session if session else self.sessionMaker() as _session:
            recordType = await _session.scalar(recordTypeQuery)

            if recordType is None: return None

            return reactionMenu.databaseMenuClassFromName(recordType)


    async def create(self, record: reactionMenu.DatabaseReactionMenu, session: Optional[AsyncSession] = None) -> reactionMenu.DatabaseReactionMenu:
        """Add a new reaction menu to the database.

        :param DatabaseReactionMenu record: The record to add
        :raises IntegrityError: If a reaction menu already exists in the database with the specified ID
        :return: the newly created reaction menu
        :rtype: DatabaseReactionMenu
        """
        async with session if session else self.sessionMaker() as _session:
            _session.add(record)

        return record
    

    async def get(self, recordId: int, session: Optional[AsyncSession] = None, withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[reactionMenu.DatabaseReactionMenu]]] = None) -> Optional[reactionMenu.DatabaseReactionMenu]:
        """Get the record with the given ID. Returns `None` if it does not exist.
        The menu is deserialized into the class named in its `menuType` field.

        :param int recordId: integer discord ID for the DatabaseReactionMenu to get
        :return: The stored record, or None if no record is found with the id
        :rtype: Optional[DatabaseReactionMenu]
        """
        async with session if session else self.sessionMaker() as _session:
            menuClass = await self.getMenuClassForRecord(recordId, session=session)
            if menuClass is None: return None

            query = select(menuClass).where(menuClass.id == recordId)

            if withOnlyFields:
                query = query.with_only_columns(*withOnlyFields)

            result = await _session.execute(query)
            row = result.one_or_none()
            return None if row is None else row.t[0]
    

    async def getOrCreate(self, record: reactionMenu.DatabaseReactionMenu, session: Optional[AsyncSession] = None) -> reactionMenu.DatabaseReactionMenu:
        async with session if session else self.sessionMaker() as _session:
            menuClass = await self.getMenuClassForRecord(record.id, session=session)
            if menuClass is None:
                return await self.create(record, session=_session)

            query = select(menuClass).where(menuClass.id == record.id)

            result = await _session.execute(query)
        
            row = result.one()
            return row[0]
