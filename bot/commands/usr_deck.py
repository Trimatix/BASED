import discord
from urllib import request
import json
from datetime import datetime
import asyncio

from . import commandsDB as botCommands
from .. import botState, lib
from ..reactionMenus import PagedReactionMenu, ReactionMenu
from ..cfg import cfg
from ..scheduling import TimedTask
from ..game import sdbGame

botCommands.addHelpSection(0, "decks")


async def cmd_add_deck(message : discord.Message, args : str, isDM : bool):
    """Add a deck to the guild."""
    if not args:
        await message.channel.send(":x: Please provide a link to the deck file generated by `make-deck`!")
        return

    callingBGuild = botState.guildsDB.getGuild(message.guild.id)

    deckMeta = json.load(request.urlopen(args))
    # if deckMeta["deck_name"] in callingBGuild.decks:

    now = datetime.utcnow()
    callingBGuild.decks[deckMeta["deck_name"].lower()] = {"meta_url": args, "creator": message.author.id, "creation_date" : str(now.year) + "-" + str(now.month) + "-" + str(now.day), "plays": 0,
                                                            "expansionNames" : list(deckMeta["expansions"].keys())}

    await message.channel.send("Deck added!")

botCommands.register("add-deck", cmd_add_deck, 0, allowDM=False, useDoc=True, helpSection="decks", forceKeepArgsCasing=True)


async def cmd_start_game(message : discord.Message, args : str, isDM : bool):
    callingBGuild = botState.guildsDB.getGuild(message.guild.id)
    if args not in callingBGuild.decks:
        await message.channel.send(":x: Unknown deck: " + args)
        return

    expansionPickerMsg = await message.channel.send("​")
    numExpansions = len(callingBGuild.decks[args]["expansionNames"])

    optionPages = {}
    embedKeys = []
    numPages = numExpansions // 5 + (0 if numExpansions % 5 == 0 else 1)
    menuTimeout = lib.timeUtil.timeDeltaFromDict(cfg.expansionPickerTimeout)
    menuTT = TimedTask.TimedTask(expiryDelta=menuTimeout, expiryFunction=sdbGame.startGameFromExpansionMenu, expiryFunctionArgs={"menuID": expansionPickerMsg.id, "deckName": args})
    callingBGuild.runningGames[message.channel] = None

    for pageNum in range(numPages):
        embedKeys.append(lib.discordUtil.makeEmbed(authorName="What expansions would you like to use?",
                                                    footerTxt="Page " + str(pageNum + 1) + " of " + str(numPages) + \
                                                        " | This menu will expire in " + lib.timeUtil.td_format_noYM(menuTimeout)))
        embedKeys[-1].add_field(name="Currently selected:", value="​", inline=False)
        optionPages[embedKeys[-1]] = {}

    for expansionNum in range(numExpansions):
        pageNum = expansionNum // 5
        pageEmbed = embedKeys[pageNum]
        optionEmoji = cfg.defaultMenuEmojis[expansionNum % 5]
        expansionName = callingBGuild.decks[args]["expansionNames"][expansionNum]
        pageEmbed.add_field(name=optionEmoji.sendable + " : " + expansionName, value="​", inline=False)
        optionPages[pageEmbed][optionEmoji] = ReactionMenu.NonSaveableSelecterMenuOption(expansionName, optionEmoji, expansionPickerMsg.id)

    expansionSelectorMenu = PagedReactionMenu.MultiPageOptionPicker(expansionPickerMsg,
        pages=optionPages, timeout=menuTT, owningBasedUser=botState.usersDB.getOrAddID(message.author.id), targetMember=message.author)

    botState.reactionMenusDB[expansionPickerMsg.id] = expansionSelectorMenu
    try:
        await expansionSelectorMenu.updateMessage()
    except discord.NotFound:
        await asyncio.sleep(2)
        await expansionSelectorMenu.updateMessage()

botCommands.register("start-game", cmd_start_game, 0, allowDM=False, useDoc=True, helpSection="decks")


async def cmd_decks(message : discord.Message, args : str, isDM : bool):
    callingBGuild = botState.guildsDB.getGuild(message.guild.id)
    await message.channel.send(", ".join(list(callingBGuild.decks.keys())))

botCommands.register("decks", cmd_decks, 0, allowDM=False, useDoc=True, helpSection="decks")