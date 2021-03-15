from __future__ import annotations

from discord import Guild

from .. import botState, lib
from ..baseClasses import serializable
from ..cfg import cfg


class BasedGuild(serializable.Serializable):
    """A class representing a guild in discord, and storing extra bot-specific information about it.

    :var id: The ID of the guild, directly corresponding to a discord guild's ID.
    :vartype id: int
    :var dcGuild: This guild's corresponding discord.Guild object
    :vartype dcGuild: discord.Guild
    """

    def __init__(self, id: int, dcGuild: Guild, commandPrefix: str = cfg.defaultCommandPrefix):
        """
        :param int id: The ID of the guild, directly corresponding to a discord guild's ID.
        :param discord.Guild guild: This guild's corresponding discord.Guild object
        """

        if not isinstance(dcGuild, Guild):
            raise lib.exceptions.NoneDCGuildObj("Given dcGuild of type '" + dcGuild.__class__.__name__ + \
                                                "', expecting discord.Guild")

        self.id = id
        self.dcGuild = dcGuild
        if not commandPrefix:
            raise ValueError("Empty command prefix provided")
        self.commandPrefix = commandPrefix


    def toDict(self, **kwargs) -> dict:
        """Serialize this BasedGuild into dictionary format to be saved to file.

        :return: A dictionary containing all information needed to reconstruct this BasedGuild
        :rtype: dict
        """
        return {"commandPrefix": self.commandPrefix}


    @classmethod
    def fromDict(cls, guildDict: dict, **kwargs) -> BasedGuild:
        """Factory function constructing a new BasedGuild object from the information
        in the provided guildDict - the opposite of BasedGuild.toDict

        :param int id: The discord ID of the guild
        :param dict guildDict: A dictionary containing all information required to build the BasedGuild object
        :return: A BasedGuild according to the information in guildDict
        :rtype: BasedGuild
        """
        if "id" not in kwargs:
            raise NameError("Required kwarg missing: id")
        guildID = kwargs["id"]

        dcGuild = botState.client.get_guild(guildID)
        if not isinstance(dcGuild, Guild):
            raise lib.exceptions.NoneDCGuildObj("Could not get guild object for id " + str(guildID))

        if "commandPrefix" in guildDict:
            return BasedGuild(guildID, dcGuild, commandPrefix=guildDict["commandPrefix"])
        return BasedGuild(guildID, dcGuild)
