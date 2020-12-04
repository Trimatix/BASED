import discord
import traceback
from datetime import datetime

from . import commandsDB as bbCommands
from .. import botState, lib

from . import util_help


async def dev_cmd_dev_help(message : discord.Message, args : str, isDM : bool):
    """dev command printing help strings for dev commands as defined in bbData

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    await util_help.util_autohelp(message, args, isDM, 3)

bbCommands.register("dev-help", dev_cmd_dev_help, 3, signatureStr="**dev-help** *[page number, section or command]*", shortHelp="Display information about developer-only commands.\nGive a specific command for detailed info about it, or give a page number or give a section name for brief info.", longHelp="Display information about developer-only commands.\nGive a specific command for detailed info about it, or give a page number or give a section name for brief info about a set of commands. These are the currently valid section names:\n- Bounties\n- Miscellaneous\n- Items\n- Channels\n- Skins")



async def dev_cmd_sleep(message : discord.Message, args : str, isDM : bool):
    """developer command saving all data to JSON and then shutting down the bot

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    await message.channel.send("shutting down.")
    await botState.client.shutdown()

bbCommands.register("sleep", dev_cmd_sleep, 3, allowDM=True, useDoc=True)


async def dev_cmd_save(message : discord.Message, args : str, isDM : bool):
    """developer command saving all databases to JSON

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    try:
        botState.client.bb_saveAllDBs()
    except Exception as e:
        print("SAVING ERROR", e.__class__.__name__)
        print(traceback.format_exc())
        await message.channel.send("failed!")
        return
    print(datetime.now().strftime("%H:%M:%S: Data saved manually!"))
    await message.channel.send("saved!")

bbCommands.register("save", dev_cmd_save, 3, allowDM=True, useDoc=True)


async def dev_cmd_say(message : discord.Message, args : str, isDM : bool):
    """developer command sending a message to the same channel as the command is called in

    :param discord.Message message: the discord message calling the command
    :param str args: string containing the message to broadcast
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if args == "":
        await message.channel.send("provide a message!")
    else:
        broadcastEmbed = None
        msg = args

        try:
            embedIndex = msg.index("embed=")
        except ValueError:
            embedIndex = -1

        if embedIndex != -1:
            msgText = msg[:embedIndex]
        else:
            msgText = msg

        if embedIndex != -1:
            msg = msg[embedIndex+len("embed="):]
            titleTxt = ""
            desc = ""
            footerTxt = ""
            thumb = ""
            img = ""
            authorName = ""
            icon = ""

            try:
                startIndex = msg.index("titleTxt='")+len("titleTxt=")+1
                endIndex = startIndex + \
                    msg[msg.index("titleTxt='")+len("titleTxt='"):].index("'")
                titleTxt = msg[startIndex:endIndex]
                msg = msg[endIndex+2:]
            except ValueError:
                pass

            try:
                startIndex = msg.index("desc='")+len("desc=")+1
                endIndex = startIndex + \
                    msg[msg.index("desc='")+len("desc='"):].index("'")
                desc = msg[startIndex:endIndex].replace("{NL}", "\n")
                msg = msg[endIndex+2:]
            except ValueError:
                pass

            try:
                startIndex = msg.index("footerTxt='")+len("footerTxt=")+1
                endIndex = startIndex + \
                    msg[msg.index("footerTxt='") +
                        len("footerTxt='"):].index("'")
                footerTxt = msg[startIndex:endIndex]
                msg = msg[endIndex+2:]
            except ValueError:
                pass

            try:
                startIndex = msg.index("thumb='")+len("thumb=")+1
                endIndex = startIndex + \
                    msg[msg.index("thumb='")+len("thumb='"):].index("'")
                thumb = msg[startIndex:endIndex]
                msg = msg[endIndex+2:]
            except ValueError:
                pass

            try:
                startIndex = msg.index("img='")+len("img=")+1
                endIndex = startIndex + \
                    msg[msg.index("img='")+len("img='"):].index("'")
                img = msg[startIndex:endIndex]
                msg = msg[endIndex+2:]
            except ValueError:
                pass

            try:
                startIndex = msg.index("authorName='")+len("authorName=")+1
                endIndex = startIndex + \
                    msg[msg.index("authorName='") +
                        len("authorName='"):].index("'")
                authorName = msg[startIndex:endIndex]
                msg = msg[endIndex+2:]
            except ValueError:
                pass

            try:
                startIndex = msg.index("icon='")+len("icon=")+1
                endIndex = startIndex + \
                    msg[msg.index("icon='")+len("icon='"):].index("'")
                icon = msg[startIndex:endIndex]
                msg = msg[endIndex+2:]
            except ValueError:
                pass

            broadcastEmbed = lib.discordUtil.makeEmbed(titleTxt=titleTxt, desc=desc, footerTxt=footerTxt,
                                       thumb=thumb, img=img, authorName=authorName, icon=icon)

            try:
                msg.index('\n')
                fieldsExist = True
            except ValueError:
                fieldsExist = False
            while fieldsExist:
                nextNL = msg.index('\n')
                try:
                    closingNL = nextNL + msg[nextNL+1:].index('\n')
                except ValueError:
                    fieldsExist = False
                else:
                    broadcastEmbed.add_field(name=msg[:nextNL].replace(
                        "{NL}", "\n"), value=msg[nextNL+1:closingNL+1].replace("{NL}", "\n"), inline=False)
                    msg = msg[closingNL+2:]
                
                if not fieldsExist:
                    broadcastEmbed.add_field(name=msg[:nextNL].replace(
                        "{NL}", "\n"), value=msg[nextNL+1:].replace("{NL}", "\n"), inline=False)

        await message.channel.send(msgText, embed=broadcastEmbed)

bbCommands.register("say", dev_cmd_say, 3, forceKeepArgsCasing=True, allowDM=True, useDoc=True)
