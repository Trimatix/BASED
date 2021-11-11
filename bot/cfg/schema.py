from carica.models import SerializableDataClass, SerializableTimedelta
from dataclasses import dataclass

from carica.models.path import SerializablePath
from ..lib.emojis import UninitializedBasedEmoji
from typing import List

@dataclass
class EmojisConfig(SerializableDataClass):
    longProcess: UninitializedBasedEmoji
    # When a user message prompts a DM to be sent, this emoji will be added to the message reactions.
    dmSent: UninitializedBasedEmoji
    cancel: UninitializedBasedEmoji
    submit: UninitializedBasedEmoji
    spiral: UninitializedBasedEmoji
    error: UninitializedBasedEmoji
    accept: UninitializedBasedEmoji
    reject: UninitializedBasedEmoji
    next: UninitializedBasedEmoji
    previous: UninitializedBasedEmoji
    numbers: List[UninitializedBasedEmoji]
    # The default emojis to list in a reaction menu
    menuOptions: List[UninitializedBasedEmoji]


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
