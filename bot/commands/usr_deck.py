from inspect import ArgSpec
import shutil
import discord
# from urllib import request
import aiohttp
import json
from datetime import datetime
import asyncio

from . import commandsDB as botCommands
from .. import botState, lib
from ..reactionMenus import SDBExpansionsPicker, reactionMenu
from ..cfg import cfg
from ..scheduling import timedTask
from ..game import sdbGame, sdbDeck
from ..users.basedGuild import BasedGuild

import os
from datetime import datetime
from ..cardRenderer import make_cards
from ..cardRenderer.lib import url_to_local_path
import pathlib


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
    callingBGuild.decks[deckMeta["deck_name"].lower()] = {"meta_url": args, "creator": message.author.id, "last_update": now.timestamp(), "plays": 0,
                                                            "expansion_names" : list(deckMeta["expansions"].keys())}

    await message.channel.send("Deck added!")

# botCommands.register("add-deck", cmd_add_deck, 0, allowDM=False, useDoc=True, helpSection="decks", forceKeepArgsCasing=True)


async def cmd_create(message : discord.Message, args : str, isDM : bool):
    if not args:
        await message.channel.send(":x: Please give a public google spreadsheet link to your deck to add.")
        return

    callingBGuild = botState.guildsDB.getGuild(message.guild.id)
    loadingMsg = await message.channel.send("Reading spreadsheet... " + cfg.defaultEmojis.loading.sendable)

    try:
        gameData = sdbDeck.collect_cards(args)
        await loadingMsg.edit(content="Reading spreadsheet... " + cfg.defaultEmojis.submit.sendable)
    except sdbDeck.gspread.SpreadsheetNotFound:
        await message.channel.send(":x: Unrecognised spreadsheet! Please make sure the file exists and is public.")
        return
    else:
        if gameData["title"] == "":
            await message.channel.send(":x: Your deck does not have a name! Please name the spreadsheet and try again.")
            return

        if len(gameData["title"]) > cfg.maxDeckNameLength:
            gameData["title"] = gameData["title"][:3]
            await message.channel.send("The maximum deck name length is " + str(cfg.maxDeckNameLength) + " characters - your deck will be called '" + gameData["title"] + "'")

        if gameData["title"].lower() in callingBGuild.decks:
            await message.channel.send(":x: A deck already exists in this server with the name '" + gameData["title"] + "' - cannot add deck.")
            return

        lowerExpansions = [expansion.lower() for expansion in gameData["expansions"]]
        for expansion in lowerExpansions:
            if lowerExpansions.count(expansion) > 1:
                await message.channel.send(":x: Deck creation failed - duplicate expansion pack name found: " + expansion)
                return
        
        unnamedFound = False
        emptyExpansions = []
        for expansion in gameData["expansions"]:
            if expansion == "":
                unnamedFound = True
            if len(gameData["expansions"][expansion]["white"]) == 0 and len(gameData["expansions"][expansion]["black"]) == 0:
                emptyExpansions.append(expansion)

        errs = ""
        
        if unnamedFound:
            errs += "\nUnnamed expansion pack detected - skipping this expansion."
            del gameData["expansions"][""]

        if len(emptyExpansions) != 0:
            errs += "\nEmpty expansion packs detected - skipping these expansions: " + ", ".join(expansion for expansion in emptyExpansions)
            for expansion in emptyExpansions:
                del gameData["expansions"][expansion]
        
        if errs != "":
            await message.channel.send(errs)

        whiteCounts = {expansion: len(gameData["expansions"][expansion]["white"]) for expansion in gameData["expansions"]}
        blackCounts = {expansion: len(gameData["expansions"][expansion]["black"]) for expansion in gameData["expansions"]}

        totalWhite = sum(whiteCounts.values())
        totalBlack = sum(blackCounts.values())
        
        if int(totalWhite / cfg.cardsPerHand) < 2:
            await message.channel.send("Deck creation failed.\nDecks must have at least " + str(2 * cfg.cardsPerHand) + " white cards.")
            return
        if totalBlack == 0:
            await message.channel.send("Deck creation failed.\nDecks must have at least 1 black card.")
            return

        loadingMsg = await message.channel.send("Drawing cards... " + cfg.defaultEmojis.loading.sendable)
        deckMeta = await make_cards.render_all(cfg.paths.decksFolder, gameData, cfg.paths.cardFont, message.guild.id, contentFontSize=cfg.cardContentFontSize, titleFontSize=cfg.cardTitleFontSize)
        if cfg.cardStorageMethod == "discord":
            deckMeta = await make_cards.store_cards_discord(cfg.paths.decksFolder, deckMeta,
                                                            botState.client.get_guild(cfg.cardsDCChannel["guild_id"]).get_channel(cfg.cardsDCChannel["channel_id"]),
                                                            message)
        elif cfg.cardStorageMethod == "local":
            deckMeta = make_cards.store_cards_local(deckMeta)
        else:
            raise ValueError("Unsupported cfg.cardStorageMethod: " + str(cfg.cardStorageMethod))

        await loadingMsg.edit(content="Drawing cards... " + cfg.defaultEmojis.submit.sendable)
        
        deckMeta["spreadsheet_url"] = args
        metaPath = cfg.paths.decksFolder + os.sep + str(message.guild.id) + os.sep + str(hash(gameData["title"])) + ".json"
        lib.jsonHandler.writeJSON(metaPath, deckMeta)
        now = datetime.utcnow()
        callingBGuild.decks[deckMeta["deck_name"].lower()] = {"meta_path": metaPath, "creator": message.author.id, "last_update" : now.timestamp(), "plays": 0,
                                                            "expansions" : {expansion: (whiteCounts[expansion], blackCounts[expansion]) for expansion in whiteCounts}, "spreadsheet_url": args, "white_count": totalWhite, "black_count": totalBlack,
                                                            "updating": False}

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

    if message.channel in callingBGuild.runningGames:
        await message.reply(":x: A game is already being played in this channel!")
        return

    if callingBGuild.decks[args]["updating"]:
        await message.channel.send(":x: This deck is currently being updated!")
        return

    if args in callingBGuild.activeDecks:
        gameDeck = callingBGuild.activeDecks[args]
    else:
        gameDeck = sdbDeck.SDBDeck(callingBGuild.decks[args]["meta_path"])
    
    reservation = sdbGame.GameChannelReservation(gameDeck)
    callingBGuild.runningGames[message.channel] = reservation

    options = {}
    optNum = 0
    for optNum in range(len(cfg.roundsPickerOptions)):
        emoji = cfg.defaultEmojis.menuOptions[optNum]
        roundsNum = cfg.roundsPickerOptions[optNum]
        options[emoji] = reactionMenu.DummyReactionMenuOption("Best of " + str(roundsNum), emoji)
    options[cfg.defaultEmojis.spiral] = reactionMenu.DummyReactionMenuOption("Free play", cfg.defaultEmojis.spiral)
    options[cfg.defaultEmojis.cancel] = reactionMenu.DummyReactionMenuOption("Cancel", cfg.defaultEmojis.cancel)

    roundsPickerMsg = await message.channel.send("​")
    roundsResult = await reactionMenu.InlineReactionMenu(roundsPickerMsg, message.author, cfg.timeouts.numRoundsPickerSeconds,
                                                    options=options, returnTriggers=list(options.keys()), titleTxt="Game Length", desc="How many rounds would you like to play?",
                                                    footerTxt=args.title() + " | This menu will expire in " + str(cfg.timeouts.numRoundsPickerSeconds) + "s").doMenu()

    if reservation.shutdownOverride:
        await message.channel.send(reservation.shutdownOverrideReason if reservation.shutdownOverrideReason else "The game was forcibly ended, likely due to an error.")
    else:
        rounds = cfg.defaultSDBRounds
        if len(roundsResult) == 1:
            if roundsResult[0] == cfg.defaultEmojis.spiral:
                rounds = -1
            elif roundsResult[0] == cfg.defaultEmojis.cancel:
                await message.channel.send("Game cancelled.")
                del callingBGuild.runningGames[message.channel]
                return
            else:
                rounds = cfg.roundsPickerOptions[cfg.defaultEmojis.menuOptions.index(roundsResult[0])]

        expansionPickerMsg = roundsPickerMsg
        expansionsData = callingBGuild.decks[args]["expansions"]
        
        menuTimeout = lib.timeUtil.timeDeltaFromDict(cfg.timeouts.expansionsPicker)
        menuTT = timedTask.TimedTask(expiryDelta=menuTimeout, expiryFunction=sdbGame.startGameFromExpansionMenu, expiryFunctionArgs={"menuID": expansionPickerMsg.id, "deckName": args, "rounds": rounds})

        expansionSelectorMenu = SDBExpansionsPicker.SDBExpansionsPicker(expansionPickerMsg, expansionsData,
                                                                        timeout=menuTT, owningBasedUser=botState.usersDB.getOrAddID(message.author.id), targetMember=message.author)

        botState.reactionMenusDB[expansionPickerMsg.id] = expansionSelectorMenu
        botState.taskScheduler.scheduleTask(menuTT)
        try:
            await expansionSelectorMenu.updateMessage()
        except discord.NotFound:
            await asyncio.sleep(2)
            await expansionSelectorMenu.updateMessage()

botCommands.register("play", cmd_start_game, 0, allowDM=False, signatureStr="**play <deck name>** *[rounds]*", shortHelp="Start a game of Super Deck Breaker! Give the name of the deck you want to play with.", helpSection="decks")


async def cmd_decks(message : discord.Message, args : str, isDM : bool):
    callingBGuild = botState.guildsDB.getGuild(message.guild.id)
    
    if len(callingBGuild.decks) == 0:
        await message.channel.send("This guild has no decks! See `" + callingBGuild.commandPrefix + "help create` for how to make decks.")
    else:

        decksEmbed = lib.discordUtil.makeEmbed(titleTxt=message.guild.name, desc="__Card Decks__", footerTxt="Super Deck Breaker",
                                                thumb=("https://cdn.discordapp.com/icons/" + str(message.guild.id) + "/" + message.guild.icon + ".png?size=64") if message.guild.icon is not None else "")
        for deckName in callingBGuild.decks:
            lastUpdate = datetime.utcfromtimestamp(callingBGuild.decks[deckName]["last_update"])
            decksEmbed.add_field(name=deckName.title(), value="Added by: <@" + str(callingBGuild.decks[deckName]["creator"]) + ">\n" + \
                                                                "Last updated " + lastUpdate.strftime("%m/%d/%Y") + "\n" + \
                                                                str(callingBGuild.decks[deckName]["plays"]) + " plays | " + str(callingBGuild.decks[deckName]["white_count"] + \
                                                                callingBGuild.decks[deckName]["black_count"]) + " cards | [sheet](" + callingBGuild.decks[deckName]["spreadsheet_url"] +")\n" + \
                                                                "Max players: " + str(int(callingBGuild.decks[deckName]["white_count"] / cfg.cardsPerHand)))
        await message.channel.send(embed=decksEmbed)

botCommands.register("decks", cmd_decks, 0, allowDM=False, helpSection="decks", signatureStr="**decks**", shortHelp="List all decks owned by this server.")


async def cmd_join(message : discord.Message, args : str, isDM : bool):
    callingBGuild = botState.guildsDB.getGuild(message.guild.id)

    if message.channel not in callingBGuild.runningGames:
        await message.channel.send(":x: There is no game currently running in this channel.")
    else:
        game = callingBGuild.runningGames[message.channel]
        if not game.started:
            await message.channel.send(":x: The game has not yet started.")
        elif game.hasDCMember(message.author):
            await message.channel.send(":x: You are already a player in this game! Find your cards hand in our DMs.")
        elif not game.allowNewPlayers:
            await message.channel.send(":x: This game is locked to new players!")
        elif len(game.players) == game.maxPlayers:
            await message.channel.send(":x: This game is full!")
        else:
            sendChannel = None

            if message.author.dm_channel is None:
                await message.author.create_dm()
            sendChannel = message.author.dm_channel
            
            try:
                await sendChannel.send("✅ You joined " + game.owner.name + "'s game!")
            except discord.Forbidden:
                await message.channel.send(":x: " + message.author.mention + " failed to join - I can't DM you! Please enable DMs from users who are not friends.")
                return

            await game.dcMemberJoinGame(message.author)


botCommands.register("join", cmd_join, 0, allowDM=False, helpSection="decks", signatureStr="**join**", shortHelp="Join the game that is currently running in the channel where you call the command")


async def cmd_leave(message : discord.Message, args : str, isDM : bool):
    callingBGuild = botState.guildsDB.getGuild(message.guild.id)

    if message.channel not in callingBGuild.runningGames or isinstance(callingBGuild.runningGames[message.channel], sdbGame.GameChannelReservation):
        await message.channel.send(":x: There is no game currently running in this channel.")
    else:
        game = callingBGuild.runningGames[message.channel]
        if not game.hasDCMember(message.author):
            await message.channel.send(":x: You have not joined the game in this channel!")
        else:
            await game.dcMemberLeaveGame(message.author)


botCommands.register("leave", cmd_leave, 0, allowDM=False, helpSection="decks", signatureStr="**leave**", shortHelp="Leave the game that is currently running in the channel where you call the command")


async def cmd_redeal(message : discord.Message, args : str, isDM : bool):
    callingBGuild = botState.guildsDB.getGuild(message.guild.id)

    if message.channel not in callingBGuild.runningGames or isinstance(callingBGuild.runningGames[message.channel], sdbGame.GameChannelReservation):
        await message.channel.send(":x: There is no game currently running in this channel.")
    else:
        game = callingBGuild.runningGames[message.channel]
        try:
            player = game.playerFromMember(message.author)
        except KeyError:
            await message.channel.send(":x: You have not joined the game in this channel!")
        else:
            if not game.started:
                await message.send(":x: Please wait until the first cards have been dealt.")
            elif player.hasRedealt:
                await message.channel.send(":x: You have already used your redeal for this game!")
            else:
                await lib.discordUtil.startLongProcess(message)
                await game.redealPlayer(player)
                await lib.discordUtil.endLongProcess(message)
                await message.reply("✅ New cards dealt!")


botCommands.register("redeal", cmd_redeal, 0, allowDM=False, helpSection="decks", signatureStr="**redeal**", shortHelp="Discard all of your cards and get a completely new hand! You may only do this once per game.")


async def cmd_rename_deck(message : discord.Message, args : str, isDM : bool):
    if not args:
        await message.channel.send(":x: Please give the name of the deck you would like to rename!")
        return

    callingBGuild = botState.guildsDB.getGuild(message.guild.id)
    if args not in callingBGuild.decks:
        await message.channel.send(":x: Unknown deck: " + args)
        return

    if callingBGuild.decks[args]["creator"] != message.author.id:
        await message.channel.send(":x: You can only rename decks that you own!")
        return

    if callingBGuild.decks[args]["updating"]:
        await message.channel.send(":x: This deck is currently being updated!")
        return
    
    await message.reply("Please give the new name for the deck, within " + str(cfg.timeouts.deckRenameSeconds) + "s: ")
    
    def newDeckNameCheck(m):
        return m.author == message.author and m.channel == message.channel
    
    try:
        newNameMsg = await botState.client.wait_for("message", check=newDeckNameCheck, timeout=cfg.timeouts.deckRenameSeconds)
    except asyncio.TimeoutError:
        await message.reply(":x: You ran out of time! Please try this command again.")
    else:
        if len(newNameMsg.content) > cfg.maxDeckNameLength:
            await newNameMsg.reply(":x: The maximum deck name length is " + str(cfg.maxDeckNameLength) + "! Please try this command again.")
        else:
            if newNameMsg.content == args:
                await newNameMsg.reply("The deck is already called that! Please try this command again.")
            if newNameMsg.content in callingBGuild.decks:
                await newNameMsg.reply(":x: A deck with that name already exists! Please try this command again.")
            else:
                callingBGuild.decks[newNameMsg.content] = callingBGuild.decks[args]
                del callingBGuild.decks[args]
                deckMeta = lib.jsonHandler.readJSON(callingBGuild.decks[newNameMsg.content]["meta_path"])
                deckMeta["deck_name"] = newNameMsg.content
                lib.jsonHandler.writeJSON(callingBGuild.decks[newNameMsg.content]["meta_path"], deckMeta)
                await newNameMsg.reply("✅ Deck renamed successfully!")


botCommands.register("rename", cmd_rename_deck, 0, allowDM=False, signatureStr="**rename <old deck name>**", shortHelp="Rename a deck that you own. Only give the current name of the deck, you will be asked for the new name afterwards.", helpSection="decks")


async def cmd_delete_deck(message : discord.Message, args : str, isDM : bool):
    if not args:
        await message.channel.send(":x: Please give the name of the deck you would like to delete!")
        return

    callingBGuild = botState.guildsDB.getGuild(message.guild.id)
    if args not in callingBGuild.decks:
        await message.channel.send(":x: Unknown deck: " + args)
        return

    if callingBGuild.decks[args]["creator"] != message.author.id:
        await message.channel.send(":x: You can only delete decks that you own!")
        return

    if callingBGuild.decks[args]["updating"]:
        await message.channel.send(":x: This deck is currently being updated!")
        return
    
    if os.path.exists(callingBGuild.decks[args]["meta_path"]):
        os.remove(callingBGuild.decks[args]["meta_path"])

    cardsDir = os.path.splitext(callingBGuild.decks[args]["meta_path"])[0]
    if os.path.isdir(cardsDir):
        shutil.rmtree(cardsDir)
        
    del callingBGuild.decks[args]
    if args in callingBGuild.activeDecks:
        del callingBGuild.activeDecks[args]

    for channel in callingBGuild.runningGames:
        if callingBGuild.runningGames[channel].deck.name == args:
            callingBGuild.runningGames[channel].shutdownOverride = True
            await channel.send("This game's deck has been deleted by the owner, so this game will end after the current round.")

    await message.channel.send("Deck removed!")


botCommands.register("delete", cmd_delete_deck, 0, allowDM=False, signatureStr="**delete <deck name>**", shortHelp="Delete a deck that you own from this server.", helpSection="decks")


async def cmd_update_deck(message : discord.Message, args : str, isDM : bool):
    if not args:
        await message.channel.send(":x: Please give the name of the deck you would like to update!")
        return

    callingBGuild: BasedGuild = botState.guildsDB.getGuild(message.guild.id)
    if args not in callingBGuild.decks:
        await message.channel.send(":x: Unknown deck: " + args)
        return

    if callingBGuild.decks[args]["creator"] != message.author.id:
        await message.channel.send(":x: You can only update decks that you own!")
        return

    if callingBGuild.decks[args]["updating"]:
        await message.channel.send(":x: This deck is already being updated!")
        return

    # lastUpdate = datetime.utcfromtimestamp(callingBGuild.decks[args]["last_update"])
    # updateCooldown = lib.timeUtil.timeDeltaFromDict(cfg.timeouts.deckUpdateCooldown)
    # if datetime.utcnow() - updateCooldown < lastUpdate:
    #     await message.channel.send(":x: Please wait at least " + lib.timeUtil.td_format_noYM(updateCooldown) \
    #                                 + " between deck updates!\nThis deck was last updated at " + lastUpdate.strftime("%H:%M."))
    #     return

    callingBGuild.decks[args]["last_update"] = -1
    callingBGuild.decks[args]["updating"] = True

    deckRunning = False
    for game in callingBGuild.runningGames.values():
        if game.deck.name == args:
            if not isinstance(callingBGuild.runningGames[message.channel], sdbGame.GameChannelReservation):
                game.deckUpdater = sdbGame.DeckUpdateRegistry(message, callingBGuild)
                deckRunning = True

    if deckRunning:
        await message.channel.send("⏳ A game is currently running with this deck! The deck will be updated once the game is over.")
    else:
        await sdbDeck.updateDeck(message, callingBGuild, args)


botCommands.register("update", cmd_update_deck, 0, allowDM=False, signatureStr="**update <deck name>**", shortHelp="Update a deck that you own in this server with any changes to the spreadsheet.\nThis does not update the deck name.", helpSection="decks")
