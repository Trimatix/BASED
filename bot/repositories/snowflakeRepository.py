from __future__ import annotations

from typing import Any, Generic, Optional, Tuple, Type, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists, delete, update
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql._typing import _ColumnsClauseArgument

from ..baseClasses.dbSnowflake import DbSnowflake
from ..lib.sql import count

TRecord = TypeVar("TRecord", bound=DbSnowflake)
TField = TypeVar("TField", bound=Any)


def idField(identifier: Type[DbSnowflake]) -> InstrumentedAttribute[int]:
    """This method exists to isolate the `type: ignore` required for accessing the record's `~TRecord.id`:attr:.
    """
    return identifier.id # type: ignore[reportGeneralTypeIssues]


class SnowflakeRepository(Generic[TRecord]):
    """Helper for performing CRUD operations on the records database.
    """
    session: AsyncSession

    def __init__(self, recordType: Type[TRecord], session: AsyncSession):
        self.session = session
        self._recordType = recordType


    async def exists(self, recordId: int) -> bool:
        """Check if a record is stored in the database with the given `~TRecord.id`:attr:.

        :param int recordId: integer discord ID for the :class:`TRecord` to search for
        :return: True if recordId corresponds to a record in the database, false if no record is found with the id
        :rtype: bool
        """
        query = select(exists(1).where(idField(self._recordType) == recordId))
        
        result = await self.session.scalar(query)
        
        return result or False
    

    async def countAllDocuments(self) -> int:
        """Count the number of records in the database.

        :return: The number of stored records.
        :rtype: int
        """
        query = count(self._recordType)
        
        result = await self.session.scalar(query)
        
        return result or False


    async def create(self, record: TRecord):
        """Create a new :class:`TRecord` object with the specified ID and add it to the database

        :param TRecord record: The record to create
        :raises IntegrityError: If a :class:`TRecord` already exists in the database with the specified :param:`~record.id`
        """
        self.session.add(record)
    

    async def get(self, recordId: int, withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[TRecord]]] = None) -> Optional[TRecord]:
        """Get the record with the given :param:`recordId`. Returns ``None`` if it does not exist.

        :param int recordId: integer discord ID for the :class:`TRecord` to get
        :return: The stored record, or ``None`` if no record is found with the :param:`recordId`
        :rtype: Optional[TRecord]
        """
        query = select(self._recordType).where(idField(self._recordType) == recordId)
        
        if withOnlyFields:
            query = query.with_only_columns(withOnlyFields)

        result = await self.session.execute(query)
        row = result.one_or_none()
        return None if row is None else row.t[0]
    

    async def getOrCreate(self, record: TRecord) -> TRecord:
        """Get the record with the given :param:`~recordId.id`, or create it if it does not exist.

        :param TRecord record: The :class:`TRecord` to get/create
        :return: The stored record
        :rtype: Optional[TRecord]
        """
        query = select(self._recordType).where(idField(self._recordType) == record.id)

        result = await self.session.execute(query)
    
        row = result.one_or_none()
        if row is not None:
            return row[0]
        
        await self.create(record)
        return record
        

    async def delete(self, recordId: int):
        """Delete the record with the given :param:`recordId`.

        :param int recordId: integer discord ID for the :class:`TRecord` to delete
        """
        query = delete(self._recordType).where(idField(self._recordType) == recordId)

        await self.session.execute(query)


    async def update(self, recordId: int, **values):
        """Update the record with the given :param:`recordId` to have the values specified in :param:`values`.

        :param int recordId: integer discord ID for the :class:`TRecord` to update
        """
        query = update(self._recordType).where(idField(self._recordType) == recordId).values(**values)

        await self.session.execute(query)


    async def upsert(self, record: TRecord):
        """Create :param:`record`, or update an existing record with :param:`record.id` to match
        the values specified on :param:`record`.

        :param TRecord record: the :class:`TRecord` values to upsert
        """
        await self.session.merge(record)
