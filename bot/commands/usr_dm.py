import discord

from . import commandsDB as botCommands
from .. import botState, lib
from ..reactionMenus import SDBDMConfigMenu
from ..game import sdbGame

botCommands.addHelpSection(0, "deck master")


async def cmd_end_game(message : discord.Message, args : str, isDM : bool):
    callingBGuild = botState.guildsDB.getGuild(message.guild.id)

    if message.channel not in callingBGuild.runningGames or isinstance(callingBGuild.runningGames[message.channel], sdbGame.GameChannelReservation):
        await message.channel.send(":x: There is no game currently running in this channel.")
    elif message.author != callingBGuild.runningGames[message.channel].owner:
        await message.channel.send(":x: This command can only be used by the deck master.")
    else:
        await message.reply("Ending game...")
        game = callingBGuild.runningGames[message.channel]
        game.shutdownOverride = True
        game.shutdownOverrideReason = "The game was ended by the deck master."
        del callingBGuild.runningGames[message.channel]


botCommands.register("end-game", cmd_end_game, 0, allowDM=False, helpSection="deck master", signatureStr="**end-game**", shortHelp="Immediately end the game that's runnning in this channel.")


async def cmd_game_config(message : discord.Message, args : str, isDM : bool):
    callingBGuild = botState.guildsDB.getGuild(message.guild.id)

    if message.channel not in callingBGuild.runningGames or isinstance(callingBGuild.runningGames[message.channel], sdbGame.GameChannelReservation):
        await message.channel.send(":x: There is no game currently running in this channel.")
    elif message.author != callingBGuild.runningGames[message.channel].owner:
        await message.channel.send(":x: This command can only be used by the deck master.")
    else:
        game = callingBGuild.runningGames[message.channel]
        if not game.started:
            await message.reply(":x: Please wait until card hands have been set up.")
        else:
            player = game.playerFromMember(message.author)
            await player.makeConfigMenu()


botCommands.register("admin", cmd_game_config, 0, allowDM=False, helpSection="deck master", signatureStr="**admin**", shortHelp="Change various settings for your running game.")