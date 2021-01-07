import discord
# from urllib import request
import aiohttp
import json
from datetime import datetime
import asyncio

from . import commandsDB as botCommands
from .. import botState, lib
from ..reactionMenus import PagedReactionMenu, ReactionMenu
from ..cfg import cfg
from ..scheduling import TimedTask
from ..game import sdbGame

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime
from ..cardRenderer import make_cards


# use creds to create a client to interact with the Google Drive API
scope = ['https://spreadsheets.google.com/feeds']
creds = ServiceAccountCredentials.from_json_keyfile_name(cfg.googleAPICred, scope)
gspread_client = gspread.authorize(creds)

def collect_cards(sheetLink):
    global gspread_client

    worksheet = gspread_client.open_by_url(sheetLink)
    expansions = {}

    for expansion in worksheet.worksheets():
        expansions[expansion.title] = {"white": [card for card in expansion.col_values(1) if card],
                                        "black": [card for card in expansion.col_values(2) if card]}

    return {"expansions": expansions, "title": worksheet.title}



botCommands.addHelpSection(0, "decks")


async def cmd_add_deck(message : discord.Message, args : str, isDM : bool):
    """Add a deck to the guild."""
    if not args:
        await message.channel.send(":x: Please provide a link to the deck file generated by `make-deck`!")
        return

    callingBGuild = botState.guildsDB.getGuild(message.guild.id)

    # deckMeta = json.load(request.urlopen(args))
    async with botState.httpClient.get(args) as resp:
        deckMeta = await resp.json()
    # if deckMeta["deck_name"] in callingBGuild.decks:

    now = datetime.utcnow()
    callingBGuild.decks[deckMeta["deck_name"].lower()] = {"meta_url": args, "creator": message.author.id, "creation_date" : str(now.year) + "-" + str(now.month) + "-" + str(now.day), "plays": 0,
                                                            "expansion_names" : list(deckMeta["expansions"].keys())}

    await message.channel.send("Deck added!")

# botCommands.register("add-deck", cmd_add_deck, 0, allowDM=False, useDoc=True, helpSection="decks", forceKeepArgsCasing=True)


async def cmd_create(message : discord.Message, args : str, isDM : bool):
    if not args:
        await message.channel.send(":x: Please give a public google spreadsheet link to your deck to add.")
        return

    callingBGuild = botState.guildsDB.getGuild(message.guild.id)
    loadingMsg = await message.channel.send("Reading spreadsheet... " + cfg.loadingEmoji.sendable)

    try:
        gameData = collect_cards(args)
        await loadingMsg.edit(content="Reading spreadsheet... " + cfg.defaultSubmitEmoji.sendable)
    except gspread.SpreadsheetNotFound:
        await message.channel.send(":x: Unrecognised spreadsheet! Please make sure the file exists and is public.")
        return
    else:
        if gameData["title"].lower() in callingBGuild.decks:
            await message.channel.send(":x: A deck already exists in this server with the name '" + gameData["title"] + "' - cannot add deck.")
            return

        whiteCount = sum(len(gameData["expansions"][expansion]["white"]) for expansion in gameData["expansions"] if "white" in gameData["expansions"][expansion])
        blackCount = sum(len(gameData["expansions"][expansion]["black"]) for expansion in gameData["expansions"] if "black" in gameData["expansions"][expansion])
        
        if int(whiteCount / cfg.cardsPerHand) < 2:
            await message.channel.send("Deck creation failed.\nDecks must have at least " + str(2 * cfg.cardsPerHand) + " white cards.")
            return
        if blackCount == 0:
            await message.channel.send("Deck creation failed.\nDecks must have at least 1 black card.")
            return

        loadingMsg = await message.channel.send("Drawing cards... " + cfg.loadingEmoji.sendable)
        deckMeta = await make_cards.render_all(botState.client.get_guild(cfg.cardsDCChannel["guild_id"]).get_channel(cfg.cardsDCChannel["channel_id"]), message, gameData, cfg.cardFont)
        await loadingMsg.edit(content="Drawing cards... " + cfg.defaultSubmitEmoji.sendable)
        
        deckMeta["spreadsheet_url"] = args
        metaPath = cfg.decksFolderPath + os.sep + str(message.guild.id) + "-" + gameData["title"] + ".json"
        lib.jsonHandler.writeJSON(metaPath, deckMeta)
        now = datetime.utcnow()
        callingBGuild.decks[deckMeta["deck_name"].lower()] = {"meta_path": metaPath, "creator": message.author.id, "creation_date" : str(now.day).zfill(2) + "-" + str(now.month).zfill(2) + "-" + str(now.year), "plays": 0,
                                                            "expansion_names" : list(deckMeta["expansions"].keys()), "spreadsheet_url": args, "white_count": whiteCount, "black_count": blackCount}

        await message.channel.send("✅ Deck added: " + gameData["title"])

botCommands.register("create", cmd_create, 0, allowDM=False, helpSection="decks", signatureStr="**create <spreadsheet link>**", forceKeepArgsCasing=True, shortHelp="Add a new deck to the server. Your cards must be given in a **public** google spreadsheet link.", longHelp="Add a new deck to the server. You must provide a link to a **public** google spreadsheet containing your new deck's cards.\n\n- Each sheet in the spreadsheet is an expansion pack\n- The **A** column of each sheet contains that expansion pack's white cards\n- The **B** columns contain black cards\n- Black cards should give spaces for white cards with **one underscore (_) per white card.**")


async def cmd_start_game(message : discord.Message, args : str, isDM : bool):
    if not args:
        await message.channel.send(":x: Please give the name of the deck you would like to play with!")
        return

    callingBGuild = botState.guildsDB.getGuild(message.guild.id)
    if args not in callingBGuild.decks:
        await message.channel.send(":x: Unknown deck: " + args)
        return

    expansionPickerMsg = await message.channel.send("​")
    numExpansions = len(callingBGuild.decks[args]["expansion_names"])

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
        expansionName = callingBGuild.decks[args]["expansion_names"][expansionNum]
        pageEmbed.add_field(name=optionEmoji.sendable + " : " + expansionName, value="​", inline=False)
        optionPages[pageEmbed][optionEmoji] = ReactionMenu.NonSaveableSelecterMenuOption(expansionName, optionEmoji, expansionPickerMsg.id)

    expansionSelectorMenu = PagedReactionMenu.MultiPageOptionPicker(expansionPickerMsg,
        pages=optionPages, timeout=menuTT, owningBasedUser=botState.usersDB.getOrAddID(message.author.id), targetMember=message.author)

    botState.reactionMenusDB[expansionPickerMsg.id] = expansionSelectorMenu
    botState.reactionMenusTTDB.scheduleTask(menuTT)
    try:
        await expansionSelectorMenu.updateMessage()
    except discord.NotFound:
        await asyncio.sleep(2)
        await expansionSelectorMenu.updateMessage()

botCommands.register("play", cmd_start_game, 0, allowDM=False, signatureStr="**play <deck name>**", shortHelp="Start a game of Super Deck Breaker! Give the name of the deck you want to play with.", helpSection="decks")


async def cmd_decks(message : discord.Message, args : str, isDM : bool):
    callingBGuild = botState.guildsDB.getGuild(message.guild.id)
    
    if len(callingBGuild.decks) == 0:
        await message.channel.send("This guild has no decks! See `" + callingBGuild.commandPrefix + "help create` for how to make decks.")
    else:

        decksEmbed = lib.discordUtil.makeEmbed(titleTxt=message.guild.name, desc="__Card Decks__", footerTxt="Super Deck Breaker",
                                                thumb=("https://cdn.discordapp.com/icons/" + str(message.guild.id) + "/" + message.guild.icon + ".png?size=64") if message.guild.icon is not None else "")
        for deckName in callingBGuild.decks:
            decksEmbed.add_field(name=deckName.title(), value="Added " + callingBGuild.decks[deckName]["creation_date"] + " by <@" + str(callingBGuild.decks[deckName]["creator"]) + ">\n" + \
                                                                str(callingBGuild.decks[deckName]["plays"]) + " plays | " + str(callingBGuild.decks[deckName]["white_count"] + \
                                                                callingBGuild.decks[deckName]["black_count"]) + " cards | [sheet](" + callingBGuild.decks[deckName]["spreadsheet_url"] +")\n" + \
                                                                "Max players: " + str(int(callingBGuild.decks[deckName]["white_count"] / cfg.cardsPerHand)))
        await message.channel.send(embed=decksEmbed)

botCommands.register("decks", cmd_decks, 0, allowDM=False, helpSection="decks", signatureStr="**decks**", shortHelp="List all decks owned by this server.")


async def cmd_join(message : discord.Message, args : str, isDM : bool):
    callingBGuild = botState.guildsDB.getGuild(message.guild.id)

    if message.channel not in callingBGuild.runningGames:
        await message.channel.send(":x: There is no game currently running in this channel.")
    elif callingBGuild.runningGames[message.channel] is None or not callingBGuild.runningGames[message.channel].started:
        await message.channel.send(":x: The game has not yet started.")
    elif callingBGuild.runningGames[message.channel].hasDCMember(message.author):
        await message.channel.send(":x: You are already a player in this game! Find your cards hand in our DMs.")
    elif len(callingBGuild.runningGames[message.channel].players) == callingBGuild.runningGames[message.channel].deck.maxPlayers:
        await message.channel.send(":x: This game is full!")
    else:
        await callingBGuild.runningGames[message.channel].dcMemberJoinGame(message.author)


botCommands.register("join", cmd_join, 0, allowDM=False, helpSection="decks", signatureStr="**join**", shortHelp="Join the game that is currently running in the channel where you call the command")


async def cmd_leave(message : discord.Message, args : str, isDM : bool):
    callingBGuild = botState.guildsDB.getGuild(message.guild.id)

    if message.channel not in callingBGuild.runningGames or callingBGuild.runningGames[message.channel] is None:
        await message.channel.send(":x: There is no game currently running in this channel.")
    else:
        await callingBGuild.runningGames[message.channel].dcMemberLeaveGame(message.author)


botCommands.register("leave", cmd_leave, 0, allowDM=False, helpSection="decks", signatureStr="**leave**", shortHelp="Leave the game that is currently running in the channel where you call the command")