# Typing imports
from __future__ import annotations
from typing import List
from . import serializable

from abc import abstractmethod, abstractclassmethod

class Aliasable(serializable.Serializable):
    """An abstract class allowing subtype instances to be identified and compared by any list of names (aliases).
    A great example and common use case is in BountyBot's bbCriminal class. Criminals are NPCs that each have a unique name.
    These names usually consist of a forename and sirname, for example 'Ganfor Kant'. Providing 'Ganfor' and 'Kant' as aliases
    allows the Ganfor Kant object to be identified by any of 'Ganfor', 'Kant', or 'Ganfor Kant', for user convenience.

    :var name: The main identifier for the object
    :vartype name: str
    :var aliases: A list of alternative identifiers for the object
    :vartype aliases: list[str]
    """

    def __init__(self, name : str, aliases : List[str], forceAllowEmpty : bool = False):
        """
        :param str name: The main identifier for the object
        :param list[str] aliases: A list of alternative identifiers for the object
        :param bool forceAllowEmpty: By default, "" is disallowed as an alias. Give True to force allow it (Default False)
        """
        if not name and not forceAllowEmpty:
            raise RuntimeError("ALIAS_CONS_NONAM: Attempted to create an aliasable with an empty name")
        self.name = name

        for alias in range(len(aliases)):
            if not aliases[alias] and not forceAllowEmpty:
                raise RuntimeError("ALIAS_CONS_EMPTALIAS: Attempted to create an aliasable with an empty alias")
            aliases[alias] = aliases[alias].lower()
        self.aliases = aliases

        if name.lower() not in aliases:
            self.aliases += [name.lower()]
    

    def __eq__(self, other : Aliasable) -> bool:
        """Decide Aliasable equality based on either object sharing the other's main name.
        If neither object has the other's main name as an alias, False will be returned regardless of whether any other aliases are shared.

        :param
        """
        return type(other) == self.getType() and self.isCalled(other.name) or other.isCalled(self.name)


    def isCalled(self, name : str) -> bool:
        """Decide whether the provided name is one of this object's aliases.

        :param str name: The name to look up in this object's aliases
        :return: True if name is either this object's name, or is one of this object's aliases.
        :rtype: bool
        """
        return name.lower() == self.name.lower() or name.lower() in self.aliases


    def removeAlias(self, name : str):
        """Remove the given name from this object's aliases. This does not affect the object's main name.

        :param str name: The alias to remove
        """
        if name.lower() in self.aliases:
            self.aliases.remove(name.lower())


    def addAlias(self, name : str):
        """Add the given name to this object's aliases.

        :param str name: The alias to add
        """
        if name.lower() not in self.aliases:
            self.aliases.append(name.lower())


    @abstractmethod
    def toDict(self, **kwargs) -> dict:
        """Serialize this object into dictionary format, to be recreated completely.

        :return: A dictionary containing all information needed to recreate this object
        :rtype: dict
        """
        return {"name": self.name, "aliases": self.aliases}


    @abstractclassmethod
    def fromDict(cls, data : dict, **kwargs) -> Aliasable:
        """Recreate a dictionary-serialized bbAliasable object 
        
        :param dict data: A dictionary containing all information needed to recreate the serialized object
        :return: A new object as specified by the attributes in data
        :rtype: bbAliasable
        """
        pass
