import discord

from . import commandsDB as botCommands
from . import util_help
from .. import botState
import os


botCommands.addHelpSection(1, "decks")


async def admin_cmd_del_deck(message : discord.Message, args : str, isDM : bool):
    """remove a deck from the guild."""
    if not args:
        await message.channel.send(":x: Please provide a deck name!")
        return

    callingBGuild = botState.guildsDB.getGuild(message.guild.id)

    if args not in callingBGuild.decks:
        await message.channel.send(":x: Unknown deck name!")
        return

    if os.path.exists(callingBGuild.decks[args]["meta_path"]):
        os.remove(callingBGuild.decks[args]["meta_path"])

    del callingBGuild.decks[args]
    if args in callingBGuild.activeDecks:
        del callingBGuild.activeDecks[args]

    for channel in callingBGuild.runningGames:
        if callingBGuild.runningGames[channel].deck.name == args:
            callingBGuild.runningGames[channel].shutdownOverride = True
            await channel.send("Due to admin override, this game will end after the current round.")

    await message.channel.send("Deck removed!")

botCommands.register("del-deck", admin_cmd_del_deck, 1, allowDM=False, useDoc=True, helpSection="decks", forceKeepArgsCasing=True)