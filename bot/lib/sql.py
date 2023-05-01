from typing import Tuple, Type
from sqlalchemy import Select, select, func

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
    return select(table).order_by(None).with_only_columns([func.count()])
