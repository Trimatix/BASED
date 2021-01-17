import discord

from . import commandsDB as botCommands
from . import util_help
from .. import botState
import os
from ..cardRenderer.lib import clear_deck_path
from ..cfg import cfg


botCommands.addHelpSection(2, "decks")
