from __future__ import annotations

from typing import Any, Generic, Optional, Tuple, Type, TypeVar

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, AsyncEngine
from sqlalchemy import select, exists, delete, update
from sqlalchemy.sql._typing import _ColumnsClauseArgument

from ..baseClasses.dbSnowflake import DbSnowflake
from ..lib.sql import count

TRecord = TypeVar("TRecord", bound=DbSnowflake)
TField = TypeVar("TField", bound=Any)

class SnowflakeDB(Generic[TRecord]):
    """Helper for performing CRUD operations on the records database.
    """
    
    def __init__(self, recordType: Type[TRecord], engine: AsyncEngine):
        self.sessionMaker = async_sessionmaker(engine)
        self._recordType = recordType


    async def exists(self, recordId: int, session: Optional[AsyncSession] = None) -> bool:
        """Check if a record is stored in the database with the given ID.

        :param int recordId: integer discord ID for the TRecord to search for
        :return: True if recordId corresponds to a record in the database, false if no record is found with the id
        :rtype: bool
        """
        query = select(exists(1).where(self._recordType.id == recordId)) # type: ignore[reportGeneralTypeIssues]
        
        async with session if session else self.sessionMaker() as _session:
            result = await _session.scalar(query)
        
        return result or False
    

    async def countAllDocuments(self, session: Optional[AsyncSession] = None) -> int:
        """Count the number of records in the database.

        :return: The number of stored records.
        :rtype: int
        """
        query = count(self._recordType)
        
        async with session if session else self.sessionMaker() as _session:
            result = await _session.scalar(query)
        
        return result or False


    async def create(self, recordId: int, session: Optional[AsyncSession] = None) -> TRecord:
        """Create a new TRecord object with the specified ID and add it to the database

        :param int recordId: integer discord ID for the record to add
        :raises IntegrityError: If a TRecord already exists in the database with the specified ID
        :return: the newly created TRecord
        :rtype: TRecord
        """
        newRecord = self._recordType(id=recordId)

        async with session if session else self.sessionMaker() as _session:
            _session.add(newRecord)

        return newRecord
    

    async def get(self, recordId: int, session: Optional[AsyncSession] = None, withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[TRecord]]] = None) -> Optional[TRecord]:
        """Get the record with the given ID. Returns `None` if it does not exist.

        :param int recordId: integer discord ID for the TRecord to get
        :return: The stored record, or None if no record is found with the id
        :rtype: Optional[TRecord]
        """
        query = select(self._recordType).where(self._recordType.id == recordId) # type: ignore[reportGeneralTypeIssues]
        
        if withOnlyFields:
            query = query.with_only_columns(*withOnlyFields)

        async with session if session else self.sessionMaker() as _session:
            result = await _session.execute(query)
            row = result.one_or_none()
            return None if row is None else row.t[0]
    

    async def getOrCreate(self, recordId: int, session: Optional[AsyncSession] = None) -> TRecord:
        query = select(self._recordType).where(self._recordType.id == recordId) # type: ignore[reportGeneralTypeIssues]

        async with session if session else self.sessionMaker() as _session:
            result = await _session.execute(query)
        
            row = result.one_or_none()
            if row is not None:
                return row[0]
            
            return await self.create(recordId, session=_session)
        

    async def delete(self, recordId: int, session: Optional[AsyncSession] = None):
        query = delete(self._recordType).where(self._recordType.id == recordId) # type: ignore[reportGeneralTypeIssues]

        async with session if session else self.sessionMaker() as _session:
            await _session.execute(query)


    async def update(self, recordId: int, session: Optional[AsyncSession] = None, **values):
        query = update(self._recordType).where(self._recordType.id == recordId).values(**values) # type: ignore[reportGeneralTypeIssues]

        async with session if session else self.sessionMaker() as _session:
            await _session.execute(query)


    async def upsert(self, recordId: int, session: Optional[AsyncSession] = None, **values):
        record = self._recordType(id=recordId, **values)

        async with session if session else self.sessionMaker() as _session:
            await _session.merge(record)