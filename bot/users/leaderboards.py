from ..baseClasses.serializable import Serializable
from collections.abc import Iterable
from types import FunctionType

class CachedLeaderboard(Serializable):
    def __init__(self, source: Iterable, predicate: FunctionType, getter: FunctionType, length: int):
        self.source = source
        self.predicate = predicate
        self.getter = getter
        self.length = length
 
