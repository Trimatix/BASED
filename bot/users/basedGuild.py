from __future__ import annotations
from typing import Optional

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

class Base(DeclarativeBase):
    pass


class BasedGuild(Base):
    """A class representing a guild in discord, and storing extra bot-specific information about it.

    :var id: The ID of the guild, directly corresponding to a discord guild's ID.
    :vartype id: int
    """
    __tablename__ = "guild"
    id: Mapped[int] = mapped_column(primary_key=True)
    commandPrefix: Mapped[Optional[str]]


    def __str__(self) -> str:
        """Get a short string summary of this BasedUser. Currently only contains the user ID and home guild ID.

        :return: A string summar of the user, containing the user ID and home guild ID.
        :rtype: str
        """
        return f"<{type(self).__name__} #" + str(self.id) + ">"