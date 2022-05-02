from .. import botState
from ..reactionMenus import reactionMenu


class ReactionMenuDB(dict):
    """A database of ReactionMenu instances.
    Currently just an extension of dict to add serialize()."""

    def serialize(self, **kwargs) -> dict:
        """Serialise all saveable ReactionMenus in this DB into a single dictionary.

        :return: A dictionary containing full dictionary descriptions of all saveable ReactionMenu instances in this database
        :rtype: dict
        """
        data = {}
        for msgID in self:
            if reactionMenu.isSaveableMenuInstance(self[msgID]):
                data[msgID] = self[msgID].serialize(**kwargs)
        return data

    
    def deserialize(d, *args, **kwargs):
        raise NotImplementedError()


async def deserialize(dbDict: dict) -> ReactionMenuDB:
    """Factory function constructing a new ReactionMenuDB from dictionary-serialized format;
    the opposite of ReactionMenuDB.serialize

    :param dict dbDict: A dictionary containing all info needed to reconstruct a ReactionMenuDB,
                        in accordance with ReactionMenuDB.serialize
    :return: A new ReactionMenuDB instance as described by dbDict
    :rtype: ReactionMenuDB
    """
    newDB = ReactionMenuDB()
    requiredAttrs = ["type", "guild", "channel"]

    for msgID in dbDict:
        menuData = dbDict[msgID]

        for attr in requiredAttrs:
            if attr not in menuData:
                botState.client.logger.log("reactionMenuDB", "deserialize",
                                    "Invalid menu dict (missing " + attr + "), ignoring and removing. " \
                                        + " ".join(foundAttr + "=" + menuData[foundAttr] \
                                            for foundAttr in requiredAttrs if foundAttr in menuData),
                                    category="reactionMenus", eventType="dictNo" + attr.capitalize())

        menuDescriptor = menuData["type"] + "(" + "/".join(str(id) \
                            for id in [menuData["guild"], menuData["channel"], msgID]) + ")"

        dcGuild = botState.client.get_guild(menuData["guild"])
        if dcGuild is None:
            dcGuild = await botState.client.fetch_guild(menuData["guild"])
            if dcGuild is None:
                botState.client.logger.log("reactionMenuDB", "deserialize",
                                    "Unrecognised guild in menu dict, ignoring and removing: " + menuDescriptor,
                                    category="reactionMenus", eventType="unknGuild")
                continue

        menuChannel = dcGuild.get_channel(menuData["channel"])
        if menuChannel is None:
            menuChannel = await dcGuild.fetch_channel(menuData["channel"])
            if menuChannel is None:
                botState.client.logger.log("reactionMenuDB", "deserialize",
                                    "Unrecognised channel in menu dict, ignoring and removing: " + menuDescriptor,
                                    category="reactionMenus", eventType="unknChannel")
                continue

        msg = await menuChannel.fetch_message(menuData["msg"])
        if msg is None:
            botState.client.logger.log("reactionMenuDB", "deserialize",
                                "Unrecognised message in menu dict, ignoring and removing: " + menuDescriptor,
                                category="reactionMenus", eventType="unknMsg")
            continue
        
        if not reactionMenu.isSaveableMenuTypeName(menuData["type"]):
            newDB[int(msgID)] = reactionMenu.saveableMenuClassFromName(menuData["type"]).deserialize(menuData, msg=msg)
        else:
            botState.client.logger.log("reactionMenuDB", "deserialize",
                                "Attempted to deserialize a non-saveable menu type, ignoring and removing. msg #" + str(msgID) \
                                    + ", type " + menuData["type"],
                                category="reactionMenus", eventType="dictUnsaveable")

    return newDB
