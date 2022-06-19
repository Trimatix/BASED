from .. import botState
from discord import NotFound, HTTPException, Forbidden # type: ignore[import]
from ..cfg import cfg


async def deleteReactionMenu(menuID: int):
    """Delete the currently active reaction menu and its message entirely, with the given message ID

    :param int menuID: The ID of the menu, corresponding with the discord ID of the menu's message
    """
    menu = botState.client.reactionMenusDB[menuID]
    try:
        await menu.msg.delete()
    except NotFound:
        pass
    if menu.msg.id in botState.client.reactionMenusDB:
        del botState.client.reactionMenusDB[menu.msg.id]


async def removeEmbedAndOptions(menuID: int):
    """Delete the currently active menu with the given ID, removing its embed and option reactions, but
    leaving the corresponding message intact.

    :param int menuID: The ID of the menu, corresponding with the discord ID of the menu's message
    """
    if menuID in botState.client.reactionMenusDB:
        menu = botState.client.reactionMenusDB[menuID]
        await menu.msg.edit(suppress=True)

        for react in menu.options:
            await menu.msg.remove_reaction(react.sendable, menu.msg.guild.me)

        del botState.client.reactionMenusDB[menu.msg.id]


async def markExpiredMenu(menuID: int):
    """Replace the message content of the given menu with cfg.expiredMenuMsg, and remove 
    the menu from the active reaction menus DB.

    :param int menuID: The ID of the menu, corresponding with the discord ID of the menu's message
    """
    menu = botState.client.reactionMenusDB[menuID]
    try:
        await menu.msg.edit(content=cfg.expiredMenuMsg)
    except HTTPException: # note: HttpException also covers NotFound and Forbidden
        pass
    if menuID in botState.client.reactionMenusDB:
        del botState.client.reactionMenusDB[menuID]


async def markExpiredMenuAndRemoveOptions(menuID: int):
    """Remove all option reactions from the menu message, replace the message content of the given menu
    with cfg.expiredMenuMsg, and remove the menu from the active reaction menus DB.

    :param int menuID: The ID of the menu, corresponding with the discord ID of the menu's message
    """
    menu = botState.client.reactionMenusDB[menuID]
    menu.msg = await menu.msg.channel.fetch_message(menu.msg.id)
    try:
        await menu.msg.clear_reactions()
    except Forbidden:
        for reaction in menu.msg.reactions:
            try:
                await reaction.remove(botState.client.user)
            except (HTTPException, NotFound):
                pass

    await markExpiredMenu(menuID)


async def expireHelpMenu(menuID: int):
    """Expire a reaction help menu, and mark it so in the discord message.
    Reset the owning user's helpMenuOwned tracker.
    """
    menu = botState.client.reactionMenusDB[menuID]
    menu.owningBasedUser.helpMenuOwned = False
    await markExpiredMenuAndRemoveOptions(menuID)
