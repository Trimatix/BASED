from __future__ import annotations
from ..users.basedUser import BasedUser
from .. import lib
from .. import botState
import traceback
from typing import List
from ..baseClasses import serializable


class UserDB(serializable.Serializable):
    """A database of BasedUser objects.
    
    :var users: Dictionary of users in the database, where values are the BasedUser objects and keys are the ids of their respective BasedUser
    :vartype users: dict[int, BasedUser]
    """

    def __init__(self):
        # Store users as a dict of user.id: user
        self.users = {}


    def idExists(self, id : int) -> bool:
        """Check if a user is stored in the database with the given ID.

        :param int id: integer discord ID for the BasedUser to search for
        :return: True if id corresponds to a user in the database, false if no user is found with the id
        :rtype: bool
        """
        return id in self.users.keys()


    def userExists(self, user : BasedUser) -> bool:
        """Check if a given BasedUser object is stored in the database.
        Currently only checks if a user with the same ID is stored in the database, not if the objects are the same.

        :param BasedUser user: a BasedUser object to check for existence
        :return: True if a BasedUser is found in the database with a matching ID, False otherwise
        :rtype: bool
        """
        return self.idExists(user.id)


    def validateID(self, id : int) -> int:
        """Internal function to assert the type of and, potentially cast, an ID.

        :param int ID: the ID to type check. Can be either int or a string consisting only of digits.
        :raise TypeError: If the ID does not conform to the above requirements.
        :return: ID if ID is an int, or int(ID) if ID is a string of digits.
        :rtype: int
        """
        # If ID is a string, ensure it can be casted to an int before casting and returning.
        if type(id) == str:
            if not lib.stringTyping.isInt(id):
                raise TypeError("user ID must be either int or string of digits")
            return int(id)
        # If ID is not a string, nor an int, throw an error.
        elif type(id) != int:
            raise TypeError("user ID must be either int or string of digits")
        # ID must be an int, so return it.
        return id
    

    def reinitUser(self, id : int):
        """Reset the stats for the user with the specified ID.

        :param int ID: The ID of the user to reset. Can be integer or a string of digits.
        :raise KeyError: If no user is found with the requested ID
        """
        id = self.validateID(id)
        # ensure the ID exists in the database
        if not self.idExists(id):
            raise KeyError("user not found: " + str(id))
        # Reset the user
        self.users[id].resetUser()


    def addID(self, id : int) -> BasedUser:
        """
        Create a new BasedUser object with the specified ID and add it to the database

        :param int id: integer discord ID for the user to add
        :raise KeyError: If a BasedUser already exists in the database with the specified ID
        :return: the newly created BasedUser
        :rtype: BasedUser
        """
        id = self.validateID(id)
        # Ensure no user exists with the specified ID in the database
        if self.idExists(id):
            raise KeyError("Attempted to add a user that is already in this UserDB")
        # Create and return a new user
        newUser = BasedUser(id)
        self.users[id] = newUser
        return newUser

    def addUser(self, userObj : BasedUser):
        """Store the given BasedUser object in the database

        :param BasedUser userObj: BasedUser to store
        :raise KeyError: If a BasedUser already exists in the database with the same ID as the given BasedUser
        """
        # Ensure no BasedUser exists in the db with the same ID as the given BasedUser
        if self.idExists(userObj.id):
            raise KeyError("Attempted to add a user that is already in this UserDB: " + str(userObj))
        # Store the passed BasedUser
        self.users[userObj.id] = userObj


    def getOrAddID(self, id : int) -> BasedUser:
        """If a BasedUser exists in the database with the requested ID, return it. If not, create and store a new BasedUser and return it.

        :param int id: integer discord ID for the user to fetch or create
        :return: the requested/created BasedUser
        :rtype: int
        """
        return self.getUser(id) if self.idExists(id) else self.addID(id)

    
    def removeID(self, id : int):
        """Remove the new BasedUser object with the specified ID from the database
        ⚠ The BasedUser object is deleted from memory.

        :param int id: integer discord ID for the user to remove
        :raise KeyError: If no BasedUser exists in the database with the specified ID
        """
        id = self.validateID(id)
        if not self.idExists(id):
            raise KeyError("user not found: " + str(id))
        del self.users[id]

    
    def getUser(self, id : int) -> BasedUser:
        """Fetch the BasedUser from the database with the given ID.

        :param int ID: integer discord ID for the user to fetch
        :return: the stored BasedUser with the given ID
        :rtype: BasedUser
        """
        id = self.validateID(id)
        return self.users[id]


    def getUsers(self) -> List[BasedUser]:
        """Get a list of all BasedUser objects stored in the database

        :return: list containing all BasedUser objects in the db
        :rtype: list[BasedUser]
        """
        return list(self.users.values())

    
    def getIDs(self) -> List[int]:
        """Get a list of all user IDs stored in the database

        :return: list containing all int discord IDs for which BasedUsers are stored in the database
        :rtype: list[int]
        """
        return list(self.users.keys())

    
    def toDict(self, **kwargs) -> dict:
        """Serialise this UserDB into dictionary format.

        :return: A dictionary containing all data needed to recreate this UserDB
        :rtype: dict
        """
        data = {}
        # Iterate over all user IDs in the database
        for id in self.getIDs():
            # Serialise each BasedUser in the database and save it, along with its ID to dict 
            # JSON stores properties as strings, so ids must be converted to str first.
            try:
                data[str(id)] = self.users[id].toDict(**kwargs)
            except Exception as e:
                botState.logger.log("UserDB", "toDict", "Error serialising BasedUser: " + e.__class__.__name__, trace=traceback.format_exc(), eventType="USERERR")
        return data

    
    def __str__(self) -> str:
        """Get summarising information about this UserDB in string format.
        Currently only the number of users stored.

        :return: A string containing summarising info about this db
        :rtype: str
        """
        return "<UserDB: " + str(len(self.users)) + " users>"


    @classmethod
    def fromDict(cls, userDBDict : dict, **kwargs) -> UserDB:
        """Construct a UserDB from a dictionary-serialised representation - the reverse of UserDB.toDict()

        :param dict userDBDict: a dictionary-serialised representation of the UserDB to construct
        :return: the new UserDB
        :rtype: UserDB
        """
        # Instance the new UserDB
        newDB = UserDB()
        # iterate over all user IDs to spawn
        for id in userDBDict.keys():
            # Construct new BasedUsers for each ID in the database
            # JSON stores properties as strings, so ids must be converted to int first.
            newDB.addUser(BasedUser.fromDict(userDBDict[id], id=int(id)))
        return newDB
