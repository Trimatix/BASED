from typing import Any, ClassVar, Protocol

from sqlalchemy.orm import Mapper, Mapped
from sqlalchemy import MetaData, FromClause

class DbSnowflake(Protocol):
    """A sqlalchemy.orm.DeclarativeBase that has an integer `id` column.
    """
    id: Mapped[int]

    # DeclarativeBase attributes
    _sa_registry: ClassVar
    registry: ClassVar[Any]
    metadata: ClassVar[MetaData]
    __name__: ClassVar
    __mapper__: ClassVar[Mapper[Any]]
    __table__: ClassVar[FromClause]
    __tablename__: Any
    __mapper_args__: Any
    __table_args__: Any

    def __init__(self, **kw): ...