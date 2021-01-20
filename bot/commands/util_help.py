import discord

from . import commandsDB as botCommands
from .. import botState, lib
from ..cfg import cfg
from ..reactionMenus import pagedReactionMenu, expiryFunctions
from ..scheduling import timedTask


async def util_autohelp(message: discord.Message, args: str, isDM: bool, userAccessLevel: int):
    """Print command help strings for the given access level as an embed.
    If a command is provided in args, the associated help string for just that command is printed.

    :param discord.Message message: the discord message calling the command
    :param str args: empty, or a single command name
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    sendChannel = None
    sendDM = True

    if message.author.dm_channel is None:
        await message.author.create_dm()
    sendChannel = message.author.dm_channel

    if sendChannel == message.channel:
        sendDM = False

    if lib.stringTyping.isInt(args):
        if int(args) < 1 or int(args) > len(botCommands.helpSectionEmbeds[userAccessLevel]):
            await message.channel.send(":x: Section number must be between 1 and " +
                                        str(len(botCommands.helpSectionEmbeds[userAccessLevel])) + "!")
            return
        args = list(botCommands.helpSectionEmbeds[userAccessLevel].keys())[int(args) - 1]
    elif args == "misc":
        args = "miscellaneous"

    try:
        if args == "":
            owningUser = botState.usersDB.getOrAddID(message.author.id)
            if owningUser.helpMenuOwned:
                await message.channel.send(":x: Please close your existing help menu before making a new one!\n" +
                                            "In case you can't find it, help menus auto exire after **" +
                                            lib.timeUtil.td_format_noYM(lib.timeUtil.timeDeltaFromDict(cfg.timeouts.helpMenu))
                                            + "**.")
                return
            owningUser.helpMenuOwned = True
            menuMsg = await sendChannel.send("‎")
            helpTT = timedTask.TimedTask(expiryDelta=lib.timeUtil.timeDeltaFromDict(
                cfg.timeouts.helpMenu), expiryFunction=expiryFunctions.expireHelpMenu, expiryFunctionArgs=menuMsg.id)
            botState.reactionMenusTTDB.scheduleTask(helpTT)
            indexEmbed = lib.discordUtil.makeEmbed(titleTxt=cfg.userAccessLevels[userAccessLevel] + " Commands",
                                                    desc="Select " + cfg.defaultEmojis.next.sendable + " to go to page one.",
                                                    thumb=botState.client.user.avatar_url_as(size=64),
                                                    footerTxt="This menu will expire in " +
                                                                lib.timeUtil.td_format_noYM(helpTT.expiryDelta) + ".")
            sectionsStr = ""
            pages = {indexEmbed: {}}
            for sectionNum in range(len(botCommands.helpSectionEmbeds[userAccessLevel])):
                sectionsStr += "\n" + str(sectionNum + 1) + ") " + \
                    list(botCommands.helpSectionEmbeds[userAccessLevel].keys())[sectionNum].title()
                # sectionsStr += "\n" + cfg.defaultEmojis.menuOptions[sectionNum + 1].sendable + " : " +
                #                 list(botCommands.helpSectionEmbeds[userAccessLevel].keys())[sectionNum].title()
                # pages[indexEmbed][cfg.defaultEmojis.menuOptions[sectionNum + 1]] =
                #                 ReactionMenu.NonSaveableReactionMenuOption(list(
                #                     botCommands.helpSectionEmbeds[userAccessLevel].keys())[sectionNum].title(),
                #                     cfg.defaultEmojis.menuOptions[sectionNum + 1], addFunc=pagedReactionMenu.menuJumpToPage,
                #                     addArgs={"menuID": menuMsg.id, "pageNum": sectionNum})
            indexEmbed.add_field(name="Contents", value=sectionsStr)
            pageNum = 0
            for helpSectionEmbedList in botCommands.helpSectionEmbeds[userAccessLevel].values():
                for helpEmbed in helpSectionEmbedList:
                    pageNum += 1
                    newEmbed = helpEmbed.copy()
                    newEmbed.set_footer(text="Page " + str(pageNum) + " of " + str(
                        botCommands.totalEmbeds[userAccessLevel]) + " | This menu will expire in " +
                        lib.timeUtil.td_format_noYM(helpTT.expiryDelta) + ".")
                    pages[newEmbed] = {}
            helpMenu = pagedReactionMenu.PagedReactionMenu(
                menuMsg, pages, timeout=helpTT, targetMember=message.author, owningBasedUser=owningUser)
            await helpMenu.updateMessage()
            botState.reactionMenusDB[menuMsg.id] = helpMenu

        elif args in botCommands.helpSectionEmbeds[userAccessLevel]:
            if len(botCommands.helpSectionEmbeds[userAccessLevel][args]) == 1:
                await sendChannel.send(embed=botCommands.helpSectionEmbeds[userAccessLevel][args][0])
            else:
                owningUser = botState.usersDB.getOrAddID(message.author.id)
                if owningUser.helpMenuOwned:
                    await message.channel.send(":x: Please close your existing help menu before making a new one!\n" +
                                                "In case you can't find it, help menus auto exire after **" +
                                                lib.timeUtil.td_format_noYM(lib.timeUtil.timeDeltaFromDict(
                                                    cfg.timeouts.helpMenu)) + "**.")
                    return
                owningUser.helpMenuOwned = True
                menuMsg = await sendChannel.send("‎")
                helpTT = timedTask.TimedTask(expiryDelta=lib.timeUtil.timeDeltaFromDict(
                    cfg.timeouts.helpMenu), expiryFunction=expiryFunctions.expireHelpMenu, expiryFunctionArgs=menuMsg.id)
                botState.reactionMenusTTDB.scheduleTask(helpTT)
                pages = {}
                for helpEmbed in botCommands.helpSectionEmbeds[userAccessLevel][args]:
                    newEmbed = helpEmbed.copy()
                    newEmbed.set_footer(text=helpEmbed.footer.text + " | This menu will expire in " +
                                        lib.timeUtil.td_format_noYM(helpTT.expiryDelta) + ".")
                    pages[newEmbed] = {}
                helpMenu = pagedReactionMenu.PagedReactionMenu(
                    menuMsg, pages, timeout=helpTT, targetMember=message.author, owningBasedUser=owningUser)
                await helpMenu.updateMessage()
                botState.reactionMenusDB[menuMsg.id] = helpMenu

        elif args in botCommands.commands[userAccessLevel] and botCommands.commands[userAccessLevel][args].allowHelp:
            helpEmbed = lib.discordUtil.makeEmbed(titleTxt=cfg.userAccessLevels[userAccessLevel] + " Commands",
                                                    desc=cfg.helpIntro +
                                                    "\n__" + botCommands.commands[userAccessLevel][args].helpSection.title() +
                                                    "__", col=discord.Colour.blue(),
                                                    thumb=botState.client.user.avatar_url_as(size=64))
            helpEmbed.add_field(name=botCommands.commands[userAccessLevel][args].signatureStr,
                                value=botCommands.commands[userAccessLevel][args].longHelp, inline=False)
            helpEmbed.add_field(name="DMable", value="Yes" if botCommands.commands[userAccessLevel][args].allowDM else "No")
            if botCommands.commands[userAccessLevel][args].aliases:
                aliasesStr = ""
                for alias in botCommands.commands[userAccessLevel][args].aliases[:-1]:
                    aliasesStr += alias + ", "
                aliasesStr += botCommands.commands[userAccessLevel][args].aliases[-1]
                helpEmbed.add_field(name="Alaises", value=aliasesStr)
            await message.channel.send(embed=helpEmbed)

        else:
            await message.channel.send(":x: Unknown command/section! See `help help` for a list of help sections.")

    except discord.Forbidden:
        await message.channel.send(":x: I can't DM you, " + message.author.display_name +
                                    "! Please enable DMs from users who are not friends.")
        return
    else:
        if sendDM:
            await message.add_reaction(cfg.defaultEmojis.dmSent.sendable)
