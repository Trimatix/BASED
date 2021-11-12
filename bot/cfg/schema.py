from carica.models import SerializableDataClass, SerializableTimedelta
from dataclasses import dataclass

from carica.models.path import SerializablePath
from ..lib.emojis import IBasedEmoji, UninitializedBasedEmoji
from typing import List, Union

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
