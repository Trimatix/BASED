from typing import cast
from .. import botState
from ..reactionMenus import reactionMenu
from ..logging import LogCategory
from discord.abc import Messageable
from carica import SerializesToDict
from ..lib.jsonHandler import JsonType

class ReactionMenuDB(dict, SerializesToDict):
    """A database of ReactionMenu instances.
    Currently just an extension of dict to add serialize()."""

    def serialize(self, **kwargs):
        """Serialise all saveable ReactionMenus in this DB into a single dictionary.

        :return: A dictionary containing full dictionary descriptions of all saveable ReactionMenu instances in this database
        :rtype: dict
        """
        data = {}
        for msgID in self:
            if reactionMenu.isSaveableMenuInstance(self[msgID]):
                data[msgID] = self[msgID].serialize(**kwargs)
        return data

    
    @classmethod
    def deserialize(cls, d, **kwargs):
        raise NotImplementedError()


async def deserialize(dbDict: JsonType) -> ReactionMenuDB:
    """Factory function constructing a new ReactionMenuDB from dictionary-serialized format;
    the opposite of ReactionMenuDB.serialize

    :param dict dbDict: A dictionary containing all info needed to reconstruct a ReactionMenuDB,
                        in accordance with ReactionMenuDB.serialize
    :return: A new ReactionMenuDB instance as described by dbDict
    :rtype: ReactionMenuDB
    """
    # lots of casting going on in this method, because pyright doesn't know the structure of a serialized reaction menu
    newDB = ReactionMenuDB()
    requiredAttrs = ["type", "guild", "channel"]

    for msgID in dbDict:
        menuData = cast(JsonType, dbDict[msgID])

        for attr in requiredAttrs:
            if attr not in menuData:
                botState.client.logger.log("reactionMenuDB", "deserialize",
                                    "Invalid menu dict (missing " + attr + "), ignoring and removing. " \
                                        + " ".join(foundAttr + "=" + str(menuData[foundAttr]) \
                                            for foundAttr in requiredAttrs if foundAttr in menuData),
                                    category=LogCategory.reactionMenus, eventType="dictNo" + attr.capitalize())

        menuDescriptor = cast(str, menuData["type"]) + "(" + "/".join(str(id) \
                            for id in [menuData["guild"], menuData["channel"], msgID]) + ")"

        dcGuild = botState.client.get_guild(cast(int, menuData["guild"]))
        if dcGuild is None:
            dcGuild = await botState.client.fetch_guild(cast(int, menuData["guild"]))
            if dcGuild is None:
                botState.client.logger.log("reactionMenuDB", "deserialize",
                                    "Unrecognised guild in menu dict, ignoring and removing: " + menuDescriptor,
                                    category=LogCategory.reactionMenus, eventType="unknGuild")
                continue

        menuChannel = dcGuild.get_channel(cast(int, menuData["channel"]))
        if menuChannel is None:
            menuChannel = await dcGuild.fetch_channel(cast(int, menuData["channel"]))
            if menuChannel is None:
                botState.client.logger.log("reactionMenuDB", "deserialize",
                                    "Unrecognised channel in menu dict, ignoring and removing: " + menuDescriptor,
                                    category=LogCategory.reactionMenus, eventType="unknChannel")
                continue
        if not isinstance(menuChannel, Messageable):
            botState.client.logger.log("reactionMenuDB", "deserialize",
                                "Cannot send messages to this channel, ignoring and removing: " + menuDescriptor,
                                category=LogCategory.reactionMenus, eventType="unknChannel")
            continue

        msg = await menuChannel.fetch_message(cast(int, menuData["msg"]))
        if msg is None:
            botState.client.logger.log("reactionMenuDB", "deserialize",
                                "Unrecognised message in menu dict, ignoring and removing: " + menuDescriptor,
                                category=LogCategory.reactionMenus, eventType="unknMsg")
            continue
        
        if not reactionMenu.isSaveableMenuTypeName(cast(str, menuData["type"])):
            newDB[int(msgID)] = reactionMenu.saveableMenuClassFromName(cast(str, menuData["type"])).deserialize(menuData, msg=msg)
        else:
            botState.client.logger.log("reactionMenuDB", "deserialize",
                                "Attempted to deserialize a non-saveable menu type, ignoring and removing. msg #" + str(msgID) \
                                    + ", type " + cast(str, menuData["type"]),
                                category=LogCategory.reactionMenus, eventType="dictUnsaveable")

    return newDB
