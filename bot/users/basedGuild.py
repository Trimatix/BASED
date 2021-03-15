from __future__ import annotations

from discord import Guild

from .. import botState, lib
from ..baseClasses import serializable
from ..cfg import cfg
from ..game import sdbGame, sdbDeck
from ..reactionMenus import SDBSignupMenu


class BasedGuild(serializable.Serializable):
    """A class representing a guild in discord, and storing extra bot-specific information about it.

    :var id: The ID of the guild, directly corresponding to a discord guild's ID.
    :vartype id: int
    :var dcGuild: This guild's corresponding discord.Guild object
    :vartype dcGuild: discord.Guild
    """

    def __init__(self, id : int, dcGuild: Guild, commandPrefix : str = cfg.defaultCommandPrefix, runningGames = {}, decks = {}, modRoleID = -1):
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
        self.runningGames = runningGames
        self.decks = decks
        self.activeDecks = {}
        self.modRoleID = modRoleID
        self.modRole = None


    async def startGameSignups(self, owner, channel, deckName, expansionNames, rounds):
        if deckName not in self.decks:
            raise NameError("Unknown deck name: " + deckName)

        if channel.guild.id != self.id:
            raise RuntimeError("Attempted to start a game in a channel not owned by this guild: " + channel.name + "#" + str(channel.id))

        if channel in self.runningGames:
            raise ValueError("Attempted to start a game in a channel which aleady contains a running game: " + channel.name + "#" + str(channel.id))

        if deckName in self.activeDecks:
            gameDeck = self.activeDecks[deckName]
        else:
            gameDeck = sdbDeck.SDBDeck(self.decks[deckName]["meta_path"])

        self.runningGames[channel] = sdbGame.SDBGame(owner, gameDeck, expansionNames, channel, rounds)

        signupMsg = await channel.send("​")
        signupMenu = SDBSignupMenu.SDBSignupMenu(signupMsg, self.runningGames[channel], lib.timeUtil.timeDeltaFromDict(cfg.timeouts.gameJoinMenu))
        botState.reactionMenusDB[signupMsg.id] = signupMenu
        await signupMenu.updateMessage()
        self.decks[deckName]["plays"] += 1


    def toDict(self, **kwargs) -> dict:
        """Serialize this BasedGuild into dictionary format to be saved to file.

        :return: A dictionary containing all information needed to reconstruct this BasedGuild
        :rtype: dict
        """
        return {"commandPrefix" : self.commandPrefix, "decks": self.decks, "modRoleID": self.modRole.id if self.modRole is not None else -1}


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
            return BasedGuild(guildID, dcGuild, commandPrefix=guildDict["commandPrefix"], decks=guildDict["decks"] if "decks" in guildDict else {}, modRoleID=guildDict["modRoleID"] if "modRoleID" in guildDict else -1)
        return BasedGuild(guildID, dcGuild, decks=guildDict["decks"] if "decks" in guildDict else {}, modRoleID=guildDict["modRoleID"] if "modRoleID" in guildDict else -1)
