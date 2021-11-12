from carica.models import SerializableDataClass, SerializableTimedelta
from dataclasses import dataclass

from carica.models.path import SerializablePath
from ..lib.emojis import BasedEmoji, IBasedEmoji, UninitializedBasedEmoji
from typing import Dict, List, Set, Tuple, Union, cast, Any

EmojisFieldType = Union[BasedEmoji, List[EmojisFieldType], Set[EmojisFieldType], Tuple[EmojisFieldType], Dict[Any, EmojisFieldType]] # type: ignore

def convertEmoji(o) -> EmojisFieldType:
    if isinstance(o, UninitializedBasedEmoji):
        return o.initialize()
    elif isinstance(o, (list, set, tuple)):
        return type(o)(convertEmoji(o) for x in o)
    elif isinstance(o, dict):
        return {k: convertEmoji(o) for k, v in o.items()}
    else:
        raise TypeError(f"Found non-UninitializedBasedEmoji object, type {type(o).__name__}: {o}")


@dataclass
class EmojisConfig(SerializableDataClass):
    longProcess: Union[UninitializedBasedEmoji, IBasedEmoji]
    # When a user message prompts a DM to be sent, this emoji will be added to the message reactions.
    dmSent: IBasedEmoji
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
