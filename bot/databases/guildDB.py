from __future__ import annotations

from ..users import basedGuild
from typing import List
from .. import botState
from ..baseClasses import serializable
from .. import lib


class GuildDB(serializable.Serializable):
    """A database of BasedGuilds.

    :var guilds: Dictionary of guild.id to guild, where guild is a BasedGuild
    :vartype guilds: dict[int, BasedGuild]
    """

    def __init__(self):
        # Store guilds as a dict of guild.id: guild
        self.guilds = {}


    def getIDs(self) -> List[int]:
        """Get a list of all guild IDs in the database.

        :return: A list containing all guild IDs (ints) stored in the database.
        :rtype: list
        """
        return list(self.guilds.keys())


    def getGuilds(self) -> List[basedGuild.BasedGuild]:
        """Get a list of all BasedGuilds in the database.

        :return: A list containing all BasedGuild objects stored in the database
        :rtype: list
        """
        return list(self.guilds.values())


    def getGuild(self, id: int) -> basedGuild.BasedGuild:
        """Get the BasedGuild object with the specified ID.

        :param str id: integer discord ID for the requested guild
        :return: BasedGuild having the requested ID
        :rtype: BasedGuild
        """
        return self.guilds[id]


    def idExists(self, id: int) -> bool:
        """Check whether a BasedGuild with a given ID exists in the database.

        :param int id: integer discord ID to check for existence
        :return: True if a BasedGuild is stored in the database with the requested ID, False otherwise
        :rtype: bool
        """
        # Search the DB for the requested ID
        try:
            self.getGuild(id)
        # No BasedGuild found, return False
        except KeyError:
            return False
        # Return True otherwise
        return True


    def guildExists(self, guild: basedGuild.BasedGuild) -> bool:
        """Check whether a BasedGuild object exists in the database.
        Existence checking is currently handled by checking if a guild with the requested ID is stored.

        :param BasedGuild guild: BasedGuild object to check for existence

        :return: True if the exact BasedGuild exists in the DB, False otherwise
        :rtype: bool
        """
        return self.idExists(guild.id)


    def addGuild(self, guild: basedGuild.BasedGuild):
        """Add a given BasedGuild object to the database.

        :param BasedGuild guild: the BasedGuild object to store
        :raise KeyError: If the the guild is already in the database
        """
        # Ensure guild is not yet in the database
        if self.guildExists(guild):
            raise KeyError("Attempted to add a guild that already exists: " + guild.id)
        self.guilds[guild.id] = guild


    def addID(self, id: int) -> basedGuild.BasedGuild:
        """Add a BasedGuild object with the requested ID to the database

        :param int id: integer discord ID to create and store a BasedGuild for
        :raise KeyError: If a BasedGuild is already stored for the requested ID

        :return: the new BasedGuild object
        :rtype: BasedGuild
        """
        # Ensure the requested ID does not yet exist in the database
        if self.idExists(id):
            raise KeyError("Attempted to add a guild that already exists: " + id)
        # Create and return a BasedGuild for the requested ID
        self.guilds[id] = basedGuild.BasedGuild(id, botState.client.get_guild(id))
        return self.guilds[id]


    def removeID(self, id: int):
        """Remove the BasedGuild with the requested ID from the database.

        :param int id: integer discord ID to remove from the database
        """
        self.guilds.pop(id)


    def removeGuild(self, guild: basedGuild.BasedGuild):
        """Remove the given BasedGuild object from the database
        Currently removes any BasedGuild sharing the given guild's ID, even if it is a different object.

        :param BasedGuild guild: the guild object to remove from the database
        """
        self.removeID(guild.id)


    def toDict(self, **kwargs) -> dict:
        """Serialise this GuildDB into dictionary format

        :return: A dictionary containing all data needed to recreate this GuildDB
        :rtype: dict
        """
        data = {}
        # Iterate over all stored guilds
        for guild in self.getGuilds():
            # Serialise and then store each guild
            # JSON stores properties as strings, so ids must be converted to str first.
            data[str(guild.id)] = guild.toDict(**kwargs)
        return data


    def __str__(self) -> str:
        """Fetch summarising information about the database, as a string
        Currently only the number of guilds stored

        :return: A string summarising this db
        :rtype: str
        """
        return "<GuildDB: " + str(len(self.guilds)) + " guilds>"


    @classmethod
    def fromDict(cls, guildDBDict: dict, **kwargs) -> GuildDB:
        """Construct a GuildDB object from dictionary-serialised format; the reverse of GuildDB.todict()

        :param dict bountyDBDict: The dictionary representation of the GuildDB to create
        :return: The new GuildDB
        :rtype: GuildDB
        """
        # Instance the new GuildDB
        newDB = GuildDB()
        # Iterate over all IDs to add to the DB
        for id in guildDBDict.keys():
            # Instance new BasedGuilds for each ID, with the provided data
            # JSON stores properties as strings, so ids must be converted to int first.
            try:
                newDB.addGuild(basedGuild.BasedGuild.fromDict(guildDBDict[id], id=int(id)))
            # Ignore guilds that don't have a corresponding dcGuild
            except lib.exceptions.NoneDCGuildObj:
                botState.logger.log("GuildDB", "fromDict", "no corresponding discord guild found for ID " + id +
                                                            ", guild removed from database",
                                    category="guildsDB", eventType="NULL_GLD")
        return newDB
