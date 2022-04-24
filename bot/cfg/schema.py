from carica.models import SerializableDataClass, SerializableTimedelta, SerializablePath # type: ignore[import]
from dataclasses import dataclass
import os
from typing import Dict, List, Set, Tuple, Union, Any, cast

from ..lib.emojis import IBasedEmoji, UninitializedBasedEmoji

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
    longProcess: Union[UninitializedBasedEmoji, IBasedEmoji]
    # When a user message prompts a DM to be sent, this emoji will be added to the message reactions.
    dmSent: Union[UninitializedBasedEmoji, IBasedEmoji]
    cancel: Union[UninitializedBasedEmoji, IBasedEmoji]
    submit: Union[UninitializedBasedEmoji, IBasedEmoji]
    spiral: Union[UninitializedBasedEmoji, IBasedEmoji]
    error: Union[UninitializedBasedEmoji, IBasedEmoji]
    accept: Union[UninitializedBasedEmoji, IBasedEmoji]
    reject: Union[UninitializedBasedEmoji, IBasedEmoji]
    next: Union[UninitializedBasedEmoji, IBasedEmoji]
    previous: Union[UninitializedBasedEmoji, IBasedEmoji]
    numbers: List[Union[UninitializedBasedEmoji, IBasedEmoji]]
    # The default emojis to list in a reaction menu
    menuOptions: List[Union[UninitializedBasedEmoji, IBasedEmoji]]


    def initializeEmojis(self):
        """Converts all fields from UninitializedBasedEmoji to BasedEmoji.
        Throws errors if initialization of any emoji failed.
        """
        for varname in self._fieldNames():
            setattr(self, varname, convertEmoji(getattr(self, varname)))


@dataclass
class TimeoutsConfig(SerializableDataClass):
    helpMenu: SerializableTimedelta
    BASED_updateCheckFrequency: SerializableTimedelta
    dataSaveFrequency: SerializableTimedelta


@dataclass
class PathsConfig(SerializableDataClass):
    # path to JSON files for database saves
    usersDB: SerializablePath
    guildsDB: SerializablePath
    reactionMenusDB: SerializablePath
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
