from ..commandsManager import heirarchicalCommandsDB
from ..cfg import cfg
import importlib

commandsDB = heirarchicalCommandsDB.HeirarchicalCommandsDB(len(cfg.userAccessLevels))


def loadCommands():
    global commandsDB
    commandsDB.clear()

    for modName in cfg.includedCommandModules:
        try:
            importlib.import_module(("" if modName.startswith(".") else ".") + modName, "bot.commands")
        except ImportError as e:
            if e == modName:
                raise ImportError("Unrecognised commands module in cfg.includedCommandModules. Please ensure the file exists, and spelling/capitalization are correct: '" + modName + "'")
            else:
                raise e

    return commandsDB
