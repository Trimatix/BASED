from .. import botState
from discord import NotFound, HTTPException, Forbidden
from ..cfg import cfg

"""Expiry function template:
    if menuID in botState.reactionMenusDB:
        menu = botState.reactionMenusDB[menuID]
        await _unscheduleMenu(menu)
    else:
        botState.logger.log("expiryFunctions", "removeEmbedAndOptions", "menu not in reactionMenusDB: " + str(menuID), category="reactionMenus", eventType="MENU_NOTFOUND")
"""


async def _unscheduleMenu(menu):
    if menu.msg.id in botState.reactionMenusDB:
        del botState.reactionMenusDB[menu.msg.id]
        
    if menu.timeout is not None:
        if not menu.timeout.isExpired():
            await menu.timeout.forceExpire(callExpiryFunc=False)


async def deleteReactionMenu(menuID: int):
    """Delete the currently active reaction menu and its message entirely, with the given message ID

    :param int menuID: The ID of the menu, corresponding with the discord ID of the menu's message
    """
    if menuID in botState.reactionMenusDB:
        menu = botState.reactionMenusDB[menuID]
        await _unscheduleMenu(menu)
        try:
            await menu.msg.delete()
        except NotFound:
            pass
    else:
        botState.logger.log("expiryFunctions", "deleteReactionMenu", "menu not in reactionMenusDB: " + str(menuID), category="reactionMenus", eventType="MENU_NOTFOUND")


async def removeEmbedAndOptions(menuID: int):
    """Delete the currently active menu with the given ID, removing its embed and option reactions, but
    leaving the corresponding message intact.

    :param int menuID: The ID of the menu, corresponding with the discord ID of the menu's message
    """
    if menuID in botState.reactionMenusDB:
        menu = botState.reactionMenusDB[menuID]
        await _unscheduleMenu(menu)

        await menu.msg.edit(suppress=True)

        for react in menu.options:
            await menu.msg.remove_reaction(react.sendable, menu.msg.guild.me)
        
        del botState.reactionMenusDB[menu.msg.id]
    
    else:
        botState.logger.log("expiryFunctions", "removeEmbedAndOptions", "menu not in reactionMenusDB: " + str(menuID), category="reactionMenus", eventType="MENU_NOTFOUND")


async def markExpiredMenu(menuID: int):
    """Replace the message content of the given menu with cfg.expiredMenuMsg, and remove 
    the menu from the active reaction menus DB.

    :param int menuID: The ID of the menu, corresponding with the discord ID of the menu's message
    """
    if menuID in botState.reactionMenusDB:
        menu = botState.reactionMenusDB[menuID]
        await _unscheduleMenu(menu)
        try:
            await menu.msg.edit(content=cfg.expiredMenuMsg)
        except NotFound:
            pass
        except HTTPException:
            pass
        except Forbidden:
            pass
    else:
        botState.logger.log("expiryFunctions", "markExpiredMenu", "menu not in reactionMenusDB: " + str(menuID), category="reactionMenus", eventType="MENU_NOTFOUND")


async def markExpiredMenuAndRemoveOptions(menuID: int):
    """Remove all option reactions from the menu message, replace the message content of the given menu
    with cfg.expiredMenuMsg, and remove the menu from the active reaction menus DB.

    :param int menuID: The ID of the menu, corresponding with the discord ID of the menu's message
    """
    if menuID in botState.reactionMenusDB:
        menu = botState.reactionMenusDB[menuID]
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
    else:
        botState.logger.log("expiryFunctions", "markExpiredMenuAndRemoveOptions", "menu not in reactionMenusDB: " + str(menuID), category="reactionMenus", eventType="MENU_NOTFOUND")


async def expireHelpMenu(menuID: int):
    """Expire a reaction help menu, and mark it so in the discord message.
    Reset the owning user's helpMenuOwned tracker.
    """
    menu = botState.reactionMenusDB[menuID]
    
    if menuID in botState.reactionMenusDB:
        menu = botState.reactionMenusDB[menuID]
        menu.owningBasedUser.helpMenuOwned = False
        await markExpiredMenuAndRemoveOptions(menuID)
    else:
        botState.logger.log("expiryFunctions", "expireHelpMenu", "menu not in reactionMenusDB: " + str(menuID), category="reactionMenus", eventType="MENU_NOTFOUND")
