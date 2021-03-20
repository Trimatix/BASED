from .. import botState
from ..reactionMenus import reactionMenu


class ReactionMenuDB(dict):
    """A database of ReactionMenu instances.
    Currently just an extension of dict to add toDict()."""

    def toDict(self, **kwargs) -> dict:
        """Serialise all saveable ReactionMenus in this DB into a single dictionary.

        :return: A dictionary containing full dictionary descriptions of all saveable ReactionMenu instances in this database
        :rtype: dict
        """
        data = {}
        for msgID in self:
            if reactionMenu.isSaveableMenuInstance(self[msgID]):
                data[msgID] = self[msgID].toDict(**kwargs)
        return data


async def fromDict(dbDict: dict) -> ReactionMenuDB:
    """Factory function constructing a new ReactionMenuDB from dictionary-serialized format;
    the opposite of ReactionMenuDB.toDict

    :param dict dbDict: A dictionary containing all info needed to reconstruct a ReactionMenuDB,
                        in accordance with ReactionMenuDB.toDict
    :return: A new ReactionMenuDB instance as described by dbDict
    :rtype: ReactionMenuDB
    """
    newDB = ReactionMenuDB()
    requiredAttrs = ["type", "guild", "channel"]

    for msgID in dbDict:
        menuData = dbDict[msgID]

        for attr in requiredAttrs:
            if attr not in menuData:
                botState.logger.log("reactionMenuDB", "fromDict",
                                    "Invalid menu dict (missing " + attr + "), ignoring and removing. " \
                                        + " ".join(foundAttr + "=" + menuData[foundAttr] \
                                            for foundAttr in requiredAttrs if foundAttr in menuData),
                                    category="reactionMenus", eventType="dictNo" + attr.capitalize)

        menuDescriptor = menuData["type"] + "(" + "/".join(str(id) \
                            for id in [menuData["guild"], menuData["channel"], msgID]) + ")"

        dcGuild = botState.client.get_guild(menuData["guild"])
        if dcGuild is None:
            dcGuild = await botState.client.fetch_guild(menuData["guild"])
            if dcGuild is None:
                botState.logger.log("reactionMenuDB", "fromDict",
                                    "Unrecognised guild in menu dict, ignoring and removing: " + menuDescriptor,
                                    category="reactionMenus", eventType="unknGuild")
                continue

        menuChannel = dcGuild.get_channel(menuData["channel"])
        if menuChannel is None:
            menuChannel = await dcGuild.fetch_channel(menuData["channel"])
            if menuChannel is None:
                botState.logger.log("reactionMenuDB", "fromDict",
                                    "Unrecognised channel in menu dict, ignoring and removing: " + menuDescriptor,
                                    category="reactionMenus", eventType="unknChannel")
                continue

        msg = await menuChannel.fetch_message(menuData["msg"])
        if msg is None:
            botState.logger.log("reactionMenuDB", "fromDict",
                                "Unrecognised message in menu dict, ignoring and removing: " + menuDescriptor,
                                category="reactionMenus", eventType="unknMsg")
            continue
        
        if not reactionMenu.isSaveableMenuTypeName(menuData["type"]):
            newDB[int(msgID)] = reactionMenu.saveableMenuClassFromName(menuData["type"]).fromDict(menuData, msg=msg)
        else:
            botState.logger.log("reactionMenuDB", "fromDict",
                                "Attempted to fromDict a non-saveable menu type, ignoring and removing. msg #" + str(msgID) \
                                    + ", type " + menuData["type"],
                                category="reactionMenus", eventType="dictUnsaveable")

    return newDB
