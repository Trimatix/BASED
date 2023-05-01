from datetime import datetime
from . import reactionMenu
from discord import Embed, Member, User
from typing import Optional, Union
from ..cfg import cfg
from ..client import BasedClient


class InMemoryConfirmationMenu(reactionMenu.InMemoryReactionMenu):
    def __init__(self, client: BasedClient, menuId: int, channelId: int,
                    ownerId: Optional[int] = None, expiryTime: Optional[datetime] = None,
                    multipleChoice: Optional[bool] = None, embed: Optional[Embed] = None):

        self.client = client

        options = [
            reactionMenu.InMemoryReactionMenuOption("Yes", cfg.defaultEmojis.accept, onAdd=self.endMenu),
            reactionMenu.InMemoryReactionMenuOption("No", cfg.defaultEmojis.reject, onAdd=self.endMenu)
        ]

        super().__init__(client, menuId, channelId, options,
                            ownerId = ownerId, expiryTime = expiryTime,
                            multipleChoice = multipleChoice, embed = embed)
        

    async def endMenu(self, user: Union[User, Member]):
        await self.end(self.client)
