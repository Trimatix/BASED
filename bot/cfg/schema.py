from carica.models import SerializableDataClass, SerializableTimedelta, SerializablePath
from carica.typeChecking import TypeOverride
from dataclasses import dataclass, field
import os
from typing import Dict, List, Set, Tuple, Union, Any, cast

from ..lib.emojis import IBasedEmoji, UninitializedBasedEmoji, BasedEmoji

EmojisFieldType = Union[IBasedEmoji, List["EmojisFieldType"], Set["EmojisFieldType"], Tuple["EmojisFieldType"], Dict[Any, "EmojisFieldType"]] # type: ignore

def convertEmoji(o) -> EmojisFieldType:
    if isinstance(o, UninitializedBasedEmoji):
        return o.initialize()
    elif isinstance(o, (list, set, tuple)):
        return cast(EmojisFieldType, type(o)(convertEmoji(x) for x in o))
    elif isinstance(o, dict):
        return {k: convertEmoji(v) for k, v in o.items()}
    else:
        raise TypeError(f"Found non-UninitializedBasedEmoji object, type {type(o).__name__}: {o}")


@dataclass
class EmojisConfig(SerializableDataClass):
    longProcess: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    # When a user message prompts a DM to be sent, this emoji will be added to the message reactions.
    dmSent: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    cancel: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    submit: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    spiral: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    error: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    accept: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    reject: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    next: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    previous: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    numbers: List[BasedEmoji] = field(default_factory=TypeOverride(List[UninitializedBasedEmoji], list))
    # The default emojis to list in a reaction menu
    menuOptions: List[BasedEmoji] = field(default_factory=TypeOverride(List[UninitializedBasedEmoji], list))


    def initializeEmojis(self):
        """Converts all fields from UninitializedBasedEmoji to BasedEmoji.
        Throws errors if initialization of any emoji failed.
        """
        for varname in self._fieldNames():
            setattr(self, varname, convertEmoji(getattr(self, varname)))


@dataclass
class TimeoutsConfig(SerializableDataClass):
    BASED_updateCheckFrequency: SerializableTimedelta
    dataSaveFrequency: SerializableTimedelta


@dataclass
class PathsConfig(SerializableDataClass):
    # path to folder to save log txts to
    logsFolder: SerializablePath

    def createMissingDirectories(self):
        # Normalize all paths and create missing directories
        for varname in self._fieldNames():
            # Normalize path
            normalized = os.path.normpath(getattr(self, varname))
            setattr(self, varname, normalized)
            
            # If the path is a file, get the path to the parent directory
            pathSplit = os.path.splitext(normalized)
            pathDir = os.path.dirname(pathSplit[0]) if pathSplit[1] else pathSplit[0]
            
            # Create missing directories
            if pathDir and not os.path.isdir(pathDir):
                os.makedirs(pathDir)


@dataclass
class BasicAccessLevelNames(SerializableDataClass):
    user: str
    serverAdmin: str
    developer: str
