from __future__ import annotations
import emoji # type: ignore[import]
from .. import botState
from . import stringTyping, exceptions
import traceback
from carica import ISerializable, PrimativeType, SerializableType # type: ignore[import]
from carica.typeChecking import objectIsShallowSerializable # type: ignore[import]
from abc import ABC, abstractmethod

from typing import Union, TYPE_CHECKING
if TYPE_CHECKING:
    from discord import PartialEmoji, Emoji # type: ignore[import]


err_UnknownEmoji = "❓"
# True to raise an UnrecognisedCustomEmoji exception when requesting an unknown custom emoji
raiseUnkownEmojis = False
logUnknownEmojis = True
# Assumption of the maximum number of unicode characters in an emoji, just to put a cap on the time complexity of
# strisUnicodeEmoji. 10 characters makes sense as a 5-long ZWJ sequence plus a variation selector.
MAX_EMOJI_LEN = 10
# Special character indicating the display mode of an emoji
VAR_SELECTOR = "️"
# Regional indicator characters. Not technically classed as emojis, so they have to be special-cased.
REGIONAL_INDICATORS = ('🇦', '🇧', '🇨', '🇩', '🇪', '🇫', '🇬', '🇭', '🇮', '🇯', '🇰', '🇱', '🇲', \
                        '🇳', '🇴', '🇵', '🇶', '🇷', '🇸', '🇹', '🇺', '🇻', '🇼', '🇽', '🇾', '🇿')


def strIsUnicodeEmoji(c: str) -> bool:
    """Decide whether a given string contrains a single unicode emoji.

    :param str c: The string to test
    :return: True if c contains exactly one character, and that character is a unicode emoji. False otherwise.
    :rtype: bool
    """
    return len(c) <= MAX_EMOJI_LEN and (emoji.emoji_count(c) == 1 or c.rstrip(VAR_SELECTOR) in REGIONAL_INDICATORS)


def strIsCustomEmoji(s: str) -> bool:
    """Decide whether the given string matches the formatting of a discord custom emoji,
    being <:NAME:ID> where NAME is the name of the emoji, and ID is the integer ID.

    :param str c: The string to test
    :return: True if s 'looks like' a discord custom emoji, matching their structure. False otherwise.
    :rtype: bool
    """
    if s.startswith("<") and s.endswith(">"):
        try:
            first = s.index(":")
            second = first + s[first + 1:].index(":") + 1
        except ValueError:
            return False
        return stringTyping.isInt(s[second + 1:-1])
    return False


class IBasedEmoji(ISerializable, ABC):
    """An interface to unify over BasedEmoji and UninitializedBasedEmoji.
    """
    def __init__(self) -> None:
        self._sendable = err_UnknownEmoji
        

    @classmethod
    @abstractmethod
    def fromPartial(cls, e: PartialEmoji, rejectInvalid: bool = False) -> BasedEmoji:
        """This method will only be valid for BasedEmoji, and not for UninitializedBasedEmoji.
        Construct a new BasedEmoji object from a given discord.PartialEmoji.

        :param bool rejectInvalid: When true, an exception is guaranteed to raise if an invalid emoji is requested,
                                    regardless of raiseUnknownEmojis (Default False)
        :raise exceptions.UnrecognisedCustomEmoji: When rejectInvalid=True is present in kwargs, and a custom emoji
                                                    is given that does not exist or the client cannot access.                                   
        :return: A BasedEmoji representing e
        :rtype: BasedEmoji
        """
        raise NotImplementedError(f"Cannot invoke the abstract implementation {cls}.fromPartial")


    @classmethod
    @abstractmethod
    def fromReaction(cls, e: Union[Emoji, PartialEmoji, str], rejectInvalid: bool = False) -> BasedEmoji:
        """This method will only be valid for BasedEmoji, and not for UninitializedBasedEmoji.
        Construct a new BasedEmoji object from a given discord.PartialEmoji, discord.Emoji, or string.

        :param e: The reaction emoji to convert to BasedEmoji
        :type e: Union[Emoji, PartialEmoji, str]
        :param bool rejectInvalid: When true, an exception is guaranteed to raise if an invalid emoji is requested,
                                    regardless of raiseUnknownEmojis (Default False)
        :raise exceptions.UnrecognisedCustomEmoji: When rejectInvalid=True is present in kwargs, and a custom emoji
                                                    is given that does not exist or the client cannot access.                                   
        :return: A BasedEmoji representing e
        :rtype: BasedEmoji
        """
        raise NotImplementedError(f"Cannot invoke the abstract implementation {cls}.fromReaction")


    @classmethod
    @abstractmethod
    def fromStr(cls, s: str, rejectInvalid: bool = False) -> BasedEmoji:
        """This method will only be valid for BasedEmoji, and not for UninitializedBasedEmoji.
        Construct a BasedEmoji object from a string containing either a unicode emoji or a discord custom emoji.
        
        s may also be a BasedEmoji (returns s), a dictionary-serialized BasedEmoji (returns BasedEmoji.deserialize(s)), or
        only an ID of a discord custom emoji (may be either str or int)

        :param str s: A string containing only one of: A unicode emoji, a discord custom emoji, or
                        the ID of a discord custom emoji.
        :param bool rejectInvalid: When true, an exception is guaranteed to raise if an invalid emoji is requested,
                                    regardless of raiseUnknownEmojis (Default False)
        :raise exceptions.UnrecognisedCustomEmoji: When rejectInvalid=True is present in kwargs, and a custom emoji
                                                    is given that does not exist or the client cannot access.                                   
        :return: A BasedEmoji representing the given string emoji
        :rtype: BasedEmoji
        """
        raise NotImplementedError(f"Cannot invoke the abstract implementation {cls}.fromStr")


    @classmethod
    @abstractmethod
    def fromUninitialized(cls, e: UninitializedBasedEmoji, rejectInvalid=True) -> BasedEmoji:
        """This method will only be valid for BasedEmoji, and not for UninitializedBasedEmoji.
        Construct a BasedEmoji object from an UninitializedBasedEmoji object.

        :param UninitializedBasedEmoji e: The emoji to initialize
        :raise exceptions.UnrecognisedCustomEmoji: When rejectInvalid=True is present in kwargs, and a custom emoji
                                                    is given that does not exist or the client cannot access.       
        :return: A BasedEmoji representing the given emoji
        :rtype: BasedEmoji
        """
        raise NotImplementedError(f"Cannot invoke the abstract implementation {cls}.fromUninitialized")


    @property
    @abstractmethod
    def sendable(self) -> str:
        """A string representation of the emoji which can be sent to discord.

        :return: A discord-compliant string representation of the emoji
        :rtype: str
        """
        raise NotImplementedError(f"Cannot invoke the abstract implementation {type(self)}.sendable")


class BasedEmoji(IBasedEmoji):
    """A class that really shouldnt be necessary, acting as a union over the str (unicode) and Emoji type emojis used
    and returned by discord. To instance this class, provide exactly one of the constructor's keyword arguments.

    :var id: The ID of the Emoji that this object represents, if isID
    :vartype id: int
    :var unicode: The string unicode emoji that this object represents, if isUnicode
    :vartype unicode: 
    :var isID: True if this object represents a custom emoji, False if it represents a unicode emoji.
    :vartype isID: bool
    :var isUnicode: False if this object represents a custom emoji, True if it represents a unicode emoji.
    :vartype isUnicode: bool
    :var sendable: A string sendable in a discord message that discord will render an emoji over.
    :vartype sendable: str
    :var EMPTY: static class variable representing an empty emoji
    :vartype EMPTY: BasedEmoji
    """
    EMPTY = None

    def __init__(self, id: int = -1, unicode: str = "", rejectInvalid: bool = False):
        """
        :param int id: The ID of the custom emoji that this object should represent.
        :param str unicode: The unicode emoji that this object should represent.
        :param bool rejectInvalid: When true, an exception is guaranteed to raise if an invalid emoji is requested,
                                    regardless of raiseUnknownEmojis (Default False)
        :raise exceptions.UnrecognisedCustomEmoji: When rejectInvalid=True is present in kwargs, and a custom emoji
                                                    is given that does not exist or the client cannot access.                                   
        """

        if id == -1 and unicode == "":
            raise ValueError("At least one of id or unicode is required")
        elif id != -1 and unicode != "":
            raise ValueError("Can only accept one of id or unicode, not both")
        if not isinstance(id, int):
            raise TypeError("Given incorrect type for BasedEmoji ID: " + type(id).__name__ + " " + str(id))
        if not isinstance(unicode, str):
            raise TypeError("Given incorrect type for BasedEmoji unicode: " + type(unicode).__name__ + " " + str(unicode))

        self.id = id
        self.unicode = unicode
        self.isID = id != -1
        self.isUnicode = not self.isID
        self._sendable = self.unicode if self.isUnicode else str(botState.client.get_emoji(self.id))
        if self.sendable == "None":
            if logUnknownEmojis:
                botState.logger.log("BasedEmoji", "init", "Unrecognised custom emoji ID in BasedEmoji constructor: " +
                                    str(self.id), trace=traceback.format_exc())
            if raiseUnkownEmojis or rejectInvalid:
                raise exceptions.UnrecognisedCustomEmoji(
                    "Unrecognised custom emoji ID in BasedEmoji constructor: " + str(self.id), self.id)
            self._sendable = err_UnknownEmoji
        self._classInit = True


    def serialize(self, **kwargs) -> dict:
        """Serialize this emoji to dictionary format for saving to file.

        :return: A dictionary containing all information needed to reconstruct this emoji.
        :rtype: dict
        """
        if self.isUnicode:
            return {"unicode": self.unicode}
        return {"id": self.id}


    def __repr__(self) -> str:
        """Get a string uniquely identifying this object, specifying what type of emoji it represents and the emoji itself.

        :return: A string identifying this object.
        :rtype: str
        """
        return "<BasedEmoji-" + ("id" if self.isID else "unicode") + ":" + (str(self.id) if self.isID else self.unicode) + ">"


    def __hash__(self) -> int:
        """Calculate a hash of this emoji, based on its repr string.
        Two BasedEmoji objects representing the same emoji will have the same repr and hash.

        :return: A hash of this emoji
        :rtype: int
        """
        return hash(repr(self))


    def __eq__(self, other) -> bool:
        """Decide if this BasedEmoji is equal to another.
        Two BasedEmojis are equal if they represent the same emoji (i.e ID/unicode) of the same type (custom/unicode)

        :param BasedEmoji other: the emoji to compare this one to
        :return: True of this emoji is semantically equal to the given emoji, False otherwise
        :rtype: bool
        """
        return type(other) == BasedEmoji and self.sendable == other.sendable


    def __str__(self) -> str:
        """Get the object's 'sendable' string.

        :return: A string sendable to discord that will be translated into an emoji by the discord client.
        :rtype: str
        """
        return self.sendable


    @classmethod
    def deserialize(cls, emojiDict: dict, **kwargs) -> BasedEmoji:
        """Construct a BasedEmoji object from its dictionary representation.
        If both an ID and a unicode representation are provided, the emoji ID will be used.

        TODO: If ID is -1, use unicode. If unicode is "", use ID.

        :param dict emojiDict: A dictionary containing either an ID (for custom emojis) or
                                a unicode emoji string (for unicode emojis)
        :param bool rejectInvalid: When true, an exception is guaranteed to raise if an invalid emoji is requested,
                                    regardless of raiseUnknownEmojis (Default False)
        :raise exceptions.UnrecognisedCustomEmoji: When rejectInvalid=True is present in kwargs, and a custom emoji
                                                    is given that does not exist or the client cannot access.                                   
        :return: A new BasedEmoji object as described in emojiDict
        :rtype: BasedEmoji
        """
        rejectInvalid = kwargs["rejectInvalid"] if "rejectInvalid" in kwargs else False

        if type(emojiDict) == BasedEmoji:
            return emojiDict
        if "id" in emojiDict:
            return BasedEmoji(id=emojiDict["id"], rejectInvalid=rejectInvalid)
        else:
            return BasedEmoji(unicode=emojiDict["unicode"], rejectInvalid=rejectInvalid)


    @classmethod
    def fromPartial(cls, e: PartialEmoji, rejectInvalid: bool = False) -> BasedEmoji:
        """Construct a new BasedEmoji object from a given discord.PartialEmoji.

        :param bool rejectInvalid: When true, an exception is guaranteed to raise if an invalid emoji is requested,
                                    regardless of raiseUnknownEmojis (Default False)
        :raise exceptions.UnrecognisedCustomEmoji: When rejectInvalid=True is present in kwargs, and a custom emoji
                                                    is given that does not exist or the client cannot access.                                   
        :return: A BasedEmoji representing e
        :rtype: BasedEmoji
        """
        if type(e) == BasedEmoji:
            return e
        if e.is_unicode_emoji():
            return BasedEmoji(unicode=e.name, rejectInvalid=rejectInvalid)
        else:
            return BasedEmoji(id=e.id, rejectInvalid=rejectInvalid)


    @classmethod
    def fromReaction(cls, e: Union[Emoji, PartialEmoji, str], rejectInvalid: bool = False) -> BasedEmoji:
        """Construct a new BasedEmoji object from a given discord.PartialEmoji, discord.Emoji, or string.

        :param e: The reaction emoji to convert to BasedEmoji
        :type e: Union[Emoji, PartialEmoji, str]
        :param bool rejectInvalid: When true, an exception is guaranteed to raise if an invalid emoji is requested,
                                    regardless of raiseUnknownEmojis (Default False)
        :raise exceptions.UnrecognisedCustomEmoji: When rejectInvalid=True is present in kwargs, and a custom emoji
                                                    is given that does not exist or the client cannot access.                                   
        :return: A BasedEmoji representing e
        :rtype: BasedEmoji
        """
        if type(e) == BasedEmoji:
            return e
        if type(e) == str:
            if strIsUnicodeEmoji(e):
                return BasedEmoji(unicode=e, rejectInvalid=rejectInvalid)
            elif strIsCustomEmoji(e):
                return BasedEmoji.fromStr(e, rejectInvalid=rejectInvalid)
            else:
                raise ValueError("Given a string that does not match any emoji format: " + e)
        if type(e) == PartialEmoji:
            return BasedEmoji.fromPartial(e, rejectInvalid=rejectInvalid)
        else:
            return BasedEmoji(id=e.id, rejectInvalid=rejectInvalid)


    @classmethod
    def fromStr(cls, s: str, rejectInvalid: bool = False) -> BasedEmoji:
        """Construct a BasedEmoji object from a string containing either a unicode emoji or a discord custom emoji.
        
        s may also be a BasedEmoji (returns s), a dictionary-serialized BasedEmoji (returns BasedEmoji.deserialize(s)), or
        only an ID of a discord custom emoji (may be either str or int)

        :param str s: A string containing only one of: A unicode emoji, a discord custom emoji, or
                        the ID of a discord custom emoji.
        :param bool rejectInvalid: When true, an exception is guaranteed to raise if an invalid emoji is requested,
                                    regardless of raiseUnknownEmojis (Default False)
        :raise exceptions.UnrecognisedCustomEmoji: When rejectInvalid=True is present in kwargs, and a custom emoji
                                                    is given that does not exist or the client cannot access.                                   
        :return: A BasedEmoji representing the given string emoji
        :rtype: BasedEmoji
        """
        if type(s) == BasedEmoji:
            return s
        if type(s) == dict:
            return BasedEmoji.deserialize(s, rejectInvalid=rejectInvalid)
        if strIsUnicodeEmoji(s):
            return BasedEmoji(unicode=s, rejectInvalid=rejectInvalid)
        elif strIsCustomEmoji(s):
            return BasedEmoji(id=int(s[s[s.index(":") + 1:].index(":") + 3:-1]), rejectInvalid=rejectInvalid)
        elif stringTyping.isInt(s):
            return BasedEmoji(id=int(s), rejectInvalid=rejectInvalid)
        else:
            raise TypeError("Expected s of type str, dict or BasedEmoji, got " + type(s).__name__)


    @classmethod
    def fromUninitialized(cls, e: UninitializedBasedEmoji, rejectInvalid=True) -> BasedEmoji:
        """Construct a BasedEmoji object from an UninitializedBasedEmoji object.

        :param UninitializedBasedEmoji e: The emoji to initialize
        :raise exceptions.UnrecognisedCustomEmoji: When rejectInvalid=True is present in kwargs, and a custom emoji
                                                    is given that does not exist or the client cannot access.       
        :return: A BasedEmoji representing the given emoji
        :rtype: BasedEmoji
        """
        # Create BasedEmoji instances based on the type of the uninitialized value
        if isinstance(e.value, int):
            return BasedEmoji(id=e.value, rejectInvalid=rejectInvalid)
        elif isinstance(e.value, str):
            return BasedEmoji.fromStr(e.value, rejectInvalid=rejectInvalid)
        elif isinstance(e.value, dict):
            return BasedEmoji.deserialize(e.value, rejectInvalid=rejectInvalid)
        # Unrecognised uninitialized value
        else:
            raise ValueError("Unrecognised UninitializedBasedEmoji value type. Expecting int, str or dict, given '" +
                                type(e.value).__name__ + "'")


    @property
    def sendable(self) -> str:
        """A string representation of the emoji which can be sent to discord.

        :return: A discord-compliant string representation of the emoji
        :rtype: str
        """
        return self._sendable


# 'static' object representing an empty/lack of emoji
BasedEmoji.EMPTY = BasedEmoji(unicode=" ")
BasedEmoji.EMPTY.isUnicode = False
BasedEmoji.EMPTY.unicode = ""
BasedEmoji.EMPTY._sendable = ""


class UninitializedBasedEmoji(IBasedEmoji):
    """A data class representing a BasedEmoji waiting to be initialized.
    No instances of this class should be present after bot client's on_ready event
    has finished executing.
    """

    def __init__(self, value):
        """
        :param value: The data to attempt to initialize an emoji with. For example, an integer ID, or
                        a string unicode character.
        """
        self.value = value

    
    def serialize(self, **kwargs) -> PrimativeType:
        """Serialize this emoji to dictionary format for saving to file.
        For an UninitializedBasedEmoji, this is simply the 'value' of the emoji.
        If the value is a Serializable type, then it will be serialized before returning.

        :return: A dictionary containing all information needed to reconstruct this emoji.
        :rtype: dict
        """
        if not objectIsShallowSerializable(self.value):
            raise ValueError(f"The emoji's value ({type(self.value).__name__}) is not serializable: {self.value}")
        elif isinstance(self.value, SerializableType):
            return self.value.serialize(**kwargs)
        else:
            return self.value


    @classmethod
    def deserialize(cls, data: PrimativeType, **kwargs) -> UninitializedBasedEmoji:
        """Recreate a serialized UninitializedBasedEmoji.
        This simply wraps the given data in a new UninitializedBasedEmoji instance, with the data as the emoji's 'value'
        field. If `data` is intended to represent a serialized object, this function is not able to infer the intended type
        from `data` by default, and `data` will be wrapped as is without deserializing. It is completely feasible to add
        type inferrence or specification as a parameter as an extension of this method.

        :param PrimativeType data: A primative to take as the value of the new emoji
        :return: A new UninitializedBasedEmoji as specified by data
        :rtype: UninitializedBasedEmoji
        """
        return UninitializedBasedEmoji(data)


    @classmethod
    def fromPartial(cls, e: PartialEmoji, rejectInvalid: bool = False) -> BasedEmoji:
        """This method is only valid on the concrete BasedEmoji class, and not UninitializedBasedEmoji.
        """
        raise NotImplementedError(f"Cannot invoke {cls}.fromPartial, this method is only valid for {BasedEmoji.__name__}")


    @classmethod
    def fromReaction(cls, e: Union[Emoji, PartialEmoji, str], rejectInvalid: bool = False) -> BasedEmoji:
        """This method is only valid on the concrete BasedEmoji class, and not UninitializedBasedEmoji.
        """
        raise NotImplementedError(f"Cannot invoke {cls}.fromReaction, this method is only valid for {BasedEmoji.__name__}")


    @classmethod
    def fromStr(cls, s: str, rejectInvalid: bool = False) -> BasedEmoji:
        """This method is only valid on the concrete BasedEmoji class, and not UninitializedBasedEmoji.
        """
        raise NotImplementedError(f"Cannot invoke {cls}.fromStr, this method is only valid for {BasedEmoji.__name__}")


    @classmethod
    def fromUninitialized(cls, e: UninitializedBasedEmoji, rejectInvalid=True) -> BasedEmoji:
        """This method is only valid on the concrete BasedEmoji class, and not UninitializedBasedEmoji.
        """
        raise NotImplementedError(f"Cannot invoke {cls}.fromUninitialized, " \
                                + f"this method is only valid for {BasedEmoji.__name__}")


    def initialize(self) -> BasedEmoji:
        """Convert this UninitializedBasedEmoji to a BasedEmoji.

        :return: This emoji converted to a fully qualified BasedEmoji
        """
        return BasedEmoji.fromUninitialized(self)

    
    @property
    def sendable(self) -> str:
        """A string representation of the emoji which can be sent to discord.

        :return: A discord-compliant string representation of the emoji
        :rtype: str
        """
        raise NotImplementedError(f"Cannot invoke {type(self)}.sendable, this method is only valid for {BasedEmoji.__name__}")
