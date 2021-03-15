from __future__ import annotations
from typing import Union, TYPE_CHECKING, Tuple, Dict
if TYPE_CHECKING:
    from discord import Member, Guild, Message

from . import stringTyping, emojis, exceptions
from .. import botState
from discord import Embed, Colour, HTTPException, Forbidden, RawReactionActionEvent, Reaction, User
from discord import DMChannel, GroupChannel, TextChannel
import random
from ..cfg import cfg


def getMemberFromRef(uRef: str, dcGuild: Guild) -> Union[Member, None]:
    """Attempt to find a member of a given discord guild object from a string or integer.
    uRef can be one of:
    - A user mention <@123456> or <@!123456>
    - A user ID 123456
    - A user name Carl
    - A user name and discriminator Carl#0324

    If the passed user reference is none of the above, or a matching user cannot be found in the requested guild,
    None is returned.

    :param str uRef: A string or integer indentifying a user within dcGuild either by mention, ID, name,
                    or name and discriminator
    :param discord.Guild dcGuild: A discord.guild in which to search for a member matching uRef
    :return: Either discord.member of a member belonging to dcGuild and matching uRef, or None if uRef is invalid
                or no matching user could be found
    :rtype: discord.Member or None
    """
    # Handle user mentions
    if stringTyping.isMention(uRef):
        return dcGuild.get_member(int(uRef.lstrip("<@!").rstrip(">")))
    # Handle IDs
    elif stringTyping.isInt(uRef):
        userAttempt = dcGuild.get_member(int(uRef))
        # handle the case where uRef may be the username (without discrim) of a user whose name consists only of digits.
        if userAttempt is not None:
            return userAttempt
    # Handle user names and user name+discrim combinations
    return dcGuild.get_member_named(uRef)


def makeEmbed(titleTxt: str = "", desc: str = "", col: Colour = Colour.blue(), footerTxt: str = "", footerIcon: str = "",
              img: str = "", thumb: str = "", authorName: str = "", icon: str = "") -> Embed:
    """Factory function building a simple discord embed from the provided arguments.

    :param str titleTxt: The title of the embed (Default "")
    :param str desc: The description of the embed; appears at the top below the title (Default "")
    :param discord.Colour col: The colour of the side strip of the embed (Default discord.Colour.blue())
    :param str footerTxt: Secondary description appearing at the bottom of the embed (Default "")
    :param str footerIcon: small Image appearing to the left of the footer text (Default "")
    :param str img: Large icon appearing as the content of the embed, left aligned like a field (Default "")
    :param str thumb: larger image appearing to the right of the title (Default "")
    :param str authorName: Secondary title for the embed (Default "")
    :param str icon: smaller image to the left of authorName. AuthorName is required for this to be displayed. (Default "")
    :return: a new discord embed as described in the given parameters
    :rtype: discord.Embed
    """
    embed = Embed(title=titleTxt, description=desc, colour=col)
    if footerTxt != "":
        embed.set_footer(text=footerTxt, icon_url=footerIcon)
    embed.set_image(url=img)
    if thumb != "":
        embed.set_thumbnail(url=thumb)
    if icon != "":
        embed.set_author(name=authorName, icon_url=icon)
    return embed


async def startLongProcess(message: Message):
    """Indicates that a long process is starting, by adding a reaction to the given message.

    :param discord.Message message: The message to react to
    """
    try:
        await message.add_reaction(cfg.defaultEmojis.longProcess.sendable)
    except (HTTPException, Forbidden):
        pass


async def endLongProcess(message: Message):
    """Indicates that a long process has finished, by removing a reaction from the given message.

    :param discord.Message message: The message to remove the reaction from
    """
    try:
        await message.remove_reaction(cfg.defaultEmojis.longProcess.sendable, botState.client.user)
    except (HTTPException, Forbidden):
        pass


async def reactionFromRaw(payload: RawReactionActionEvent) -> Tuple[Message, Union[User, Member], emojis.BasedEmoji]:
    """Retrieve complete Reaction and user info from a RawReactionActionEvent payload.

    :param RawReactionActionEvent payload: Payload describing the reaction action
    :return: The message whose reactions changed, the user who completed the action, and the emoji that changed.
    :rtype: Tuple[Message, Union[User, Member], BasedEmoji]
    """
    emoji = None
    user = None
    message = None

    if payload.member is None:
        # Get the channel containing the reacted message
        if payload.guild_id is None:
            channel = botState.client.get_channel(payload.channel_id)
        else:
            guild = botState.client.get_guild(payload.guild_id)
            if guild is None:
                return None, None, None
            channel = guild.get_channel(payload.channel_id)

        # Individual handling for each channel type for efficiency
        if isinstance(channel, DMChannel):
            if channel.recipient.id == payload.user_id:
                user = channel.recipient
            else:
                user = channel.me
        elif isinstance(channel, GroupChannel):
            # Group channels should be small and far between, so iteration is fine here.
            for currentUser in channel.recipients:
                if currentUser.id == payload.user_id:
                    user = currentUser
                if user is None:
                    user = channel.me
        # Guild text channels
        elif isinstance(channel, TextChannel):
            user = channel.guild.get_member(payload.user_id)
        else:
            return None, None, None

        # Fetch the reacted message (api call)
        message = await channel.fetch_message(payload.message_id)

    # If a reacting member was given, the guild can be inferred from the member.
    else:
        user = payload.member
        message = await payload.member.guild.get_channel(payload.channel_id).fetch_message(payload.message_id)

    if message is None:
        return None, None, None

    # Convert reacted emoji to BasedEmoji
    try:
        emoji = emojis.BasedEmoji.fromPartial(payload.emoji, rejectInvalid=True)
    except exceptions.UnrecognisedCustomEmoji:
        return None, None, None

    return message, user, emoji


def messageArgsFromStr(msgStr: str) -> Dict[str, Union[str, Embed]]:
    """Transform a string description of the arguments to pass to a discord.Message constructor into type-correct arguments.

    To specify message content, simply place it at the beginning of msgStr.
    To specify an embed, give the kwarg embed=
        To give kwargs for the embed, give the kwarg name, an equals sign, then value of the kwarg encased in single quotes.

        Use makeEmbed-compliant kwarg names as follows:
            titleTxt for the embed title
            desc for the embed description
            footerTxt for the text content of the footer
            footerIcon for the URL to the image to display to the left of footerTxt
            thumb for the URL to the image to display in the top right of the embed
            img for the URL to the image to display in the main embed content
            authorName for smaller text to display in place of the title 
            icon for the URL to the image to display to the left of authorName
        
        To give fields for the embed, give field names and values separated by a new line.
        {NL} in any field will be replaced with a new line.

    :param str msgStr: A string description of the message args to create, as defined above
    :return: The message content from msgStr, and an embed as described by the kwargs and fields in msgStr.
    :rtype: Dict[str, Union[str, Embed]]
    """
    msgEmbed = None

    try:
        embedIndex = msgStr.index("embed=")
    except ValueError:
        msgText = msgStr
    else:
        msgText, msgStr = msgStr[:embedIndex], msgStr[embedIndex + len("embed="):]

        embedKwargs = { "titleTxt":     "",
                        "desc":         "",
                        "footerTxt":    "",
                        "footerIcon":   "",
                        "thumb":        "",
                        "img":          "",
                        "authorName":   "",
                        "icon":         ""}

        for argName in embedKwargs:
            try:
                startStr = argName + "='"
                startIndex = msgStr.index(startStr) + len(startStr)
                endIndex = startIndex + \
                    msgStr[msgStr.index(startStr) + len(startStr):].index("'")
                embedKwargs[argName] = msgStr[startIndex:endIndex]
                msgStr = msgStr[endIndex + 2:]
            except ValueError:
                pass
            
        msgEmbed = makeEmbed(**embedKwargs)

        try:
            msgStr.index('\n')
            fieldsExist = True
        except ValueError:
            fieldsExist = False
        while fieldsExist:
            nextNL = msgStr.index('\n')
            try:
                closingNL = nextNL + msgStr[nextNL + 1:].index('\n')
            except ValueError:
                fieldsExist = False
            else:
                msgEmbed.add_field(name=msgStr[:nextNL].replace("{NL}", "\n"),
                                            value=msgStr[nextNL + 1:closingNL + 1].replace("{NL}", "\n"),
                                            inline=False)
                msgStr = msgStr[closingNL + 2:]

            if not fieldsExist:
                msgEmbed.add_field(name=msgStr[:nextNL].replace("{NL}", "\n"),
                                            value=msgStr[nextNL + 1:].replace("{NL}", "\n"),
                                            inline=False)

    return {"content": msgText, "embed": msgEmbed}
