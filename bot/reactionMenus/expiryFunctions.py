from typing import cast
from discord import ClientUser, HTTPException, Forbidden # type: ignore[import]
from ..cfg import cfg
from ..client import BasedClient

from sqlalchemy.ext.asyncio import AsyncSession


async def _findMenu(client: BasedClient, menuID: int, session: AsyncSession):
    menu = client.inMemoryReactionMenusDB.get(menuID, None)
    if menu is not None: return True, menu

    return False, await client.databaseReactionMenusDB.get(menuID, session=session)


async def _deleteRecord(inMemory: bool, client: BasedClient, menuID: int, session: AsyncSession):
    if inMemory:
        client.inMemoryReactionMenusDB.pop(menuID, None)
    else:
        await client.databaseReactionMenusDB.delete(menuID, session=session)


async def deleteReactionMenu(client: BasedClient, menuID: int):
    """Delete the currently active reaction menu and its message entirely, with the given message ID

    :param int menuID: The ID of the menu, corresponding with the discord ID of the menu's message
    """
    async with client.sessionMaker() as session:
        inMemory, menu = await _findMenu(client, menuID, session)
        if menu is None: return
        
        msg = client.get_partial_messageable(menu.channelId).get_partial_message(menuID)

        try:
            await msg.delete()
        except HTTPException: # note: HttpException also covers NotFound and Forbidden
            pass
        
        await _deleteRecord(inMemory, client, menuID, session)


async def removeEmbedAndOptions(client: BasedClient, menuID: int):
    """Delete the currently active menu with the given ID, removing its embed and option reactions, but
    leaving the corresponding message intact.

    :param int menuID: The ID of the menu, corresponding with the discord ID of the menu's message
    """
    async with client.sessionMaker() as session:
        inMemory, menu = await _findMenu(client, menuID, session)
        if menu is None: return
        
        msg = client.get_partial_messageable(menu.channelId).get_partial_message(menuID)

        await msg.edit(embed=None)

        for react in await menu.getOptions(session=session):
            await msg.remove_reaction(react.emoji if isinstance(react.emoji, str) else react.emoji.sendable, cast(ClientUser, client.user))

        await _deleteRecord(inMemory, client, menuID, session)


async def markExpiredMenu(client: BasedClient, menuID: int):
    """Replace the message content of the given menu with cfg.expiredMenuMsg, and remove 
    the menu from the active reaction menus DB.

    :param int menuID: The ID of the menu, corresponding with the discord ID of the menu's message
    """
    async with client.sessionMaker() as session:
        inMemory, menu = await _findMenu(client, menuID, session)
        if menu is None: return

        msg = client.get_partial_messageable(menu.channelId).get_partial_message(menuID)

        try:
            await msg.edit(content=cfg.expiredMenuMsg)
        except HTTPException: # note: HttpException also covers NotFound and Forbidden
            pass

        await _deleteRecord(inMemory, client, menuID, session)


async def markExpiredMenuAndRemoveOptions(client: BasedClient, menuID: int):
    """Remove all option reactions from the menu message, replace the message content of the given menu
    with cfg.expiredMenuMsg, and remove the menu from the active reaction menus DB.

    :param int menuID: The ID of the menu, corresponding with the discord ID of the menu's message
    """
    async with client.sessionMaker() as session:
        inMemory, menu = await _findMenu(client, menuID, session)
        if menu is None: return

        msg = client.get_partial_messageable(menu.channelId).get_partial_message(menuID)

        try:
            await msg.clear_reactions()
        except Forbidden:
            msg = await msg.fetch()
            for reaction in msg.reactions:
                try:
                    await reaction.remove(cast(ClientUser, client.user))
                except HTTPException: # note: HttpException also covers NotFound and Forbidden
                    pass

        try:
            await msg.edit(content=cfg.expiredMenuMsg)
        except HTTPException: # note: HttpException also covers NotFound and Forbidden
            pass

        await _deleteRecord(inMemory, client, menuID, session)
