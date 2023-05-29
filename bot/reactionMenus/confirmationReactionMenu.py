from typing import Optional, Union
from datetime import datetime

from discord import Embed, Member, User

from sqlalchemy.ext.asyncio import AsyncSession

from . import reactionMenu
from ..cfg import cfg
from ..client import BasedClient


class InMemoryConfirmationMenu(reactionMenu.InMemoryReactionMenu):
    def __init__(self, client: BasedClient, menuId: int, channelId: int,
                    ownerId: Optional[int] = None, expiryTime: Optional[datetime] = None,
                    multipleChoice: Optional[bool] = None, embed: Optional[Embed] = None):

        options = [
            reactionMenu.InMemoryReactionMenuOption("Yes", cfg.defaultEmojis.accept, onAdd=self.endMenu),
            reactionMenu.InMemoryReactionMenuOption("No", cfg.defaultEmojis.reject, onAdd=self.endMenu)
        ]

        super().__init__(client, menuId, channelId, options,
                            ownerId = ownerId, expiryTime = expiryTime,
                            multipleChoice = multipleChoice, embed = embed)
        

    async def endMenu(self, client, user: Union[User, Member], session: Optional[AsyncSession] = None):
        await self.end(client, session=session)
