from __future__ import annotations
from typing import Union, TYPE_CHECKING, Tuple
if TYPE_CHECKING:
    from discord import Member, Guild, Message

from . import stringTyping
from .. import botState
from discord import Embed, Colour, HTTPException, Forbidden, RawReactionActionEvent, Reaction, User
import random
from ..cfg import cfg


def getMemberFromRef(uRef : str, dcGuild : Guild) -> Union[Member, None]:
    """Attempt to find a member of a given discord guild object from a string or integer.
    uRef can be one of:
    - A user mention <@123456> or <@!123456>
    - A user ID 123456
    - A user name Carl
    - A user name and discriminator Carl#0324

    If the passed user reference is none of the above, or a matching user cannot be found in the requested guild, None is returned.

    :param str uRef: A string or integer indentifying a user within dcGuild either by mention, ID, name, or name and discriminator
    :param discord.Guild dcGuild: A discord.guild in which to search for a member matching uRef
    :return: Either discord.member of a member belonging to dcGuild and matching uRef, or None if uRef is invalid or no matching user could be found
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


def makeEmbed(titleTxt : str = "", desc : str = "", col : Colour = Colour.blue(), footerTxt : str = "",
        img : str = "", thumb : str = "", authorName : str = "", icon : str = "") -> Embed:
    """Factory function building a simple discord embed from the provided arguments.

    :param str titleTxt: The title of the embed (Default "")
    :param str desc: The description of the embed; appears at the top below the title (Default "")
    :param discord.Colour col: The colour of the side strip of the embed (Default discord.Colour.blue())
    :param str footerTxt: Secondary description appearing at the bottom of the embed (Default "")
    :param str img: Large icon appearing as the content of the embed, left aligned like a field (Default "")
    :param str thumb: larger image appearing to the right of the title (Default "")
    :param str authorName: Secondary title for the embed (Default "")
    :param str icon: smaller image to the left of authorName. AuthorName is required for this to be displayed. (Default "")
    :return: a new discord embed as described in the given parameters
    :rtype: discord.Embed
    """
    embed = Embed(title=titleTxt, description=desc, colour=col)
    if footerTxt != "":
        embed.set_footer(text=footerTxt)
    embed.set_image(url=img)
    if thumb != "":
        embed.set_thumbnail(url=thumb)
    if icon != "":
        embed.set_author(name=authorName, icon_url=icon)
    return embed


async def startLongProcess(message : Message):
    """Indicates that a long process is starting, by adding a reaction to the given message.

    :param discord.Message message: The message to react to
    """
    try:
        await message.add_reaction(cfg.longProcessEmoji.sendable)
    except (HTTPException, Forbidden):
        pass


async def endLongProcess(message : Message):
    """Indicates that a long process has finished, by removing a reaction from the given message.

    :param discord.Message message: The message to remove the reaction from
    """
    try:
        await message.remove_reaction(cfg.longProcessEmoji.sendable, botState.client.user)
    except (HTTPException, Forbidden):
        pass


def randomColour():
    """Generate a completely random discord.Colour.

    :return: A discord.Colour with randomized r, g and b components.
    :rtype: discord.Colour
    """
    return Colour.from_rgb(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))


async def rawReactionPayloadToReaction(payload : RawReactionActionEvent) -> Tuple[Reaction, Union[User, Member]]:
    """Retrieve complete Reaction and user info from a RawReactionActionEvent payload.

    :param RawReactionActionEvent payload: Payload describing the reaction action
    :return: The current state of the reaction, and the user who completed the action.
    :rtype: Tuple[Reaction, Union[User, Member]]
    """
    if payload.guild_id is None:
        message = await botState.client.get_channel(payload.channel_id).fetch_message(payload.message_id)
    else:
        message = botState.client.get_guild(payload.guild_id).get_channel(payload.channel_id).fetch_message(payload.message_id)
    
    if message is None:
        return None, None

    react = None
    for currentReact in message.reactions:
        if currentReact.emoji == payload.emoji:
            react = currentReact
            break

    if react is None:
        return None, None

    reactingMember = payload.member
    if payload.member is None:
        async for currentUser in react.users():
            if currentUser.id == payload.user_id:
                reactingMember = currentUser
                break
    
    if reactingMember is None:
        return None, None

    return react, reactingMember