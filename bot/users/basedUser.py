from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

class Base(DeclarativeBase):
    pass


class BasedUser(Base):
    """A user of the bot. There is currently no guarantee that user still shares any guilds with the bot,
    though this is planned to change in the future.

    :var id: The user's unique ID. The same as their unique discord ID.
    :vartype id: int
    """
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)


    def __str__(self) -> str:
        """Get a short string summary of this BasedUser. Currently only contains the user ID and home guild ID.

        :return: A string summar of the user, containing the user ID and home guild ID.
        :rtype: str
        """
        return f"<{type(self).__name__} #" + str(self.id) + ">"
