from typing import Any, Optional, Tuple, Type
from sqlalchemy import Select, select, func
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from ..baseClasses.declarativeBaseProtocol import DeclarativeBaseProtocol

def count(table: Type[DeclarativeBaseProtocol]) -> Select[Tuple[int]]:
    """Count documents. Can be extended with the usual `where()` etc.

    ```py
    result: Optional[int] = await session.scalar(count(MyTable).where(MyTable.someField == someValue))
    ```

    sources:
    https://stackoverflow.com/a/65775282
    https://gist.github.com/hest/8798884

    :param table: The table in which to query
    :type table: Type[DeclarativeBase]
    :return: A selectable that retrieves a count
    :rtype: Select[Tuple[int]]
    """
    return select(table).order_by(None).with_only_columns(func.count())


class SessionSharer:
    def __init__(self, session: Optional[AsyncSession], sessionMaker: async_sessionmaker[AsyncSession]) -> None:
        self._session = session
        self._sessionMaker = sessionMaker
        self._newSession = session is None


    async def __aenter__(self):
        if self._session is None:
            self._session = self._sessionMaker()
            await self._session.__aenter__()

        return self


    async def __aexit__(self, type_: Any, value: Any, traceback: Any) -> None:
        await self.session.commit()
        if self._newSession:
            await self.session.__aexit__(type_, value, traceback)


    @property
    def session(self):
        if self._session is None:
            raise RuntimeError("Cannot access session before __aenter__")
        return self._session