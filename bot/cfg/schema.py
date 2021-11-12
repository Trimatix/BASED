from carica.models import SerializableDataClass, SerializableTimedelta
from dataclasses import dataclass

from carica.models.path import SerializablePath
from ..lib.emojis import IBasedEmoji
from typing import List

@dataclass
class EmojisConfig(SerializableDataClass):
    longProcess: IBasedEmoji
    # When a user message prompts a DM to be sent, this emoji will be added to the message reactions.
    dmSent: IBasedEmoji
    cancel: IBasedEmoji
    submit: IBasedEmoji
    spiral: IBasedEmoji
    error: IBasedEmoji
    accept: IBasedEmoji
    reject: IBasedEmoji
    next: IBasedEmoji
    previous: IBasedEmoji
    numbers: List[IBasedEmoji]
    # The default emojis to list in a reaction menu
    menuOptions: List[IBasedEmoji]


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
