from discord.activity import Game
from .sdbGame import SDBGame
from .sdbPlayer import SDBPlayer
from abc import ABC, abstractmethod
import inspect

class GameOption(ABC):
    def __init__(self, game: "SDBGame"):
        self.game = game
    

    @abstractmethod
    def get(self) -> str:
        pass


    @abstractmethod
    async def set(self, value):
        pass


class PrimativeOption(GameOption):
    def __init__(self, t: type, game: "SDBGame", optionVarName: str):
        super().__init__(game)
        if not inspect.isclass(t):
            raise TypeError("t must be a class. Given " + type(t).__name__)
        self.t = type
        if type(getattr(game, optionVarName)) != self.t:
            raise TypeError("Attempted to create a " + type(self).__name__ + " for a non " + t.__name__ + " attribute: " + str(optionVarName) + " of type "+ type(getattr(game, optionVarName)).__name__)
        self.optionVarName = optionVarName


    def get(self) -> str:
        return str(getattr(self.game, self.optionVarName))


    async def set(self, value):
        if type(value) != self.t:
            raise TypeError("Attempted to set a " + type(self).__name__ + " to a non " + t.__name__ + " value: " + str(value) + " of type "+ type(value).__name__)
        setattr(self.game, self.optionVarName, value)


class BoolOption(PrimativeOption):
    def __init__(self, game: "SDBGame", optionVarName: str):
        super().__init__(bool, game, optionVarName)

    
    def get(self) -> str:
        return "✅" if getattr(self.game, self.optionVarName) else "❎"


class StrOption(PrimativeOption):
    def __init__(self, game: "SDBGame", optionVarName: str):
        super().__init__(str, game, optionVarName)


class FloatOption(PrimativeOption):
    def __init__(self, game: "SDBGame", optionVarName: str):
        super().__init__(float, game, optionVarName)


class IntOption(PrimativeOption):
    def __init__(self, game: "SDBGame", optionVarName: str):
        super().__init__(int, game, optionVarName)


class ListOption(GameOption):
    def __init__(self, game: "SDBGame", optionName: str, options: list):
        super().__init__(game)
        self.optionName = optionName
        self.options = options

    
    def



class OwnerOption(GameOption):
    def get(self) -> str:
        return self.game.owner.mention

    
    async def set(self, value):
