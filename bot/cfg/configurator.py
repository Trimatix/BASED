from . import cfg
import toml
import os
from ..lib.emojis import UninitializedBasedEmoji
from typing import Dict, Any

# List of cfg attribute names that are not config variables
ignoredVarNames = ("__name__", "__doc__", "__package__", "__loader__", "__spec__",
                   "__file__", "__cached__", "__builtins__", "UninitializedBasedEmoji")

# List of cfg.defaultEmojis keys that are UninitializedBasedEmoji
emojiVars = []
# List of cfg.defaultEmojis keys that are List[UninitializedBasedEmoji]
emojiListVars = []

CFG_FILE_EXT = ".toml"

# Populate and validate emojiVars and emojiListVars
for varname, varvalue in cfg.defaultEmojis.items():
    # Populate emojiVars
    if type(varvalue) == UninitializedBasedEmoji:
        emojiVars.append(varname)
        continue
    # Populate emojiListVars
    elif type(varvalue) == list:
        onlyEmojis = True
        # Ensure emoji lists only contain emojis
        for item in varvalue:
            if type(item) != UninitializedBasedEmoji:
                onlyEmojis = False
                break
        if onlyEmojis:
            emojiListVars.append(varname)
            continue

    # Ensure emoji variables only contain emojis
    raise ValueError("Invalid config variable in cfg.defaultEmojis: " +
                        "Emoji config variables must be either UninitializedBasedEmoji or List[UninitializedBasedEmoji]")


class ConfigProxy:
    """Similar to a dictionary, except attributes are dot-accessed.
    
    :var attrnames: A list of all attribute names in the config
    :vartype attrnames: List[str]
    """

    def __init__(self, attrs: Dict[str, Any]):
        """
        :param attrs: A dictionary representing a mapping from attribute name to attribute value
        :type attrs: Dict[str, any]
        """
        self.attrNames = attrs.keys()
        for varname, varvalue in attrs.items():
            setattr(self, varname, varvalue)


def init():
    """Initialize the loaded (or default) config to be ready for use by the bot.
    This method should be called before importing your bot to ensure that config attributes can be accessed.

    Normalizes path config variables, creates any referenced directories that do not exist,
    and loads cfg.paths, cfg.defaultEmojis and cfg.timeouts into ConfigProxys.
    """
    # Normalize all paths and create missing directories
    for varname in cfg.paths:
        cfg.paths[varname] = os.path.normpath(cfg.paths[varname])
        if not os.path.isdir(os.path.dirname(cfg.paths[varname])):
            os.makedirs(os.path.dirname(cfg.paths[varname]))
    
    # Load ConfigProxys
    cfg.defaultEmojis = ConfigProxy(cfg.defaultEmojis)
    cfg.timeouts = ConfigProxy(cfg.timeouts)
    cfg.paths = ConfigProxy(cfg.paths)


def makeDefaultCfg(fileName: str = "defaultCfg" + CFG_FILE_EXT):
    """Create a config file containing all configurable variables with their default values.
    The name of the generated file may optionally be specified.

    fileName may also be a path, either relative or absolute. If missing directories are specified
    in fileName, they will be created.

    If fileName already exists, then the generated file will be renamed with an incrementing number extension.

    :param str fileName: Path to the file to generate (Default "defaultCfg.toml")
    :return: path to the generated config file
    :rtype: str
    """
    # Ensure fileName is toml
    if not fileName.endswith(CFG_FILE_EXT):
        print(fileName)
        raise ValueError("file name must end with " + CFG_FILE_EXT)

    # Create missing directories
    fileName = os.path.abspath(os.path.normpath(fileName))
    if not os.path.isdir(os.path.dirname(fileName)):
        os.makedirs(os.path.dirname(fileName))

    # If fileName already exists, make a new one by adding a number onto fileName.
    fileName = fileName.split(CFG_FILE_EXT)[0]
    cfgPath = fileName
    
    currentExt = 0
    while os.path.exists(cfgPath + CFG_FILE_EXT):
        currentExt += 1
        cfgPath = fileName + "-" + str(currentExt)

    cfgPath += CFG_FILE_EXT

    # Read default config values
    defaults = {varname: varvalue for varname, varvalue in vars(cfg).items() if varname not in ignoredVarNames}
    # Read default emoji values
    for varname in emojiVars:
        defaults["defaultEmojis"][varname] = cfg.defaultEmojis[varname].value
    # Read default emoji list values
    for varname in emojiListVars:
        working = []
        for item in defaults["defaultEmojis"][varname]:
            working.append(item.value)

        defaults["defaultEmojis"][varname] = working

    # Dump to toml and write to file
    with open(cfgPath, "w", encoding="utf-8") as f:
        f.write(toml.dumps(defaults))

    # Print and return path to new file
    print("Created " + cfgPath)
    return cfgPath


def loadCfg(cfgFile: str):
    """Load the values from a specified config file into attributes of the python cfg module.
    All config attributes are optional.

    :param str cfgFile: Path to the file to load. Can be relative or absolute.
    """
    # Ensure the given config is toml
    if not cfgFile.endswith(CFG_FILE_EXT):
        raise ValueError("config files must be TOML")
    
    # Load from toml to dictionary
    with open(cfgFile, "r", encoding="utf-8") as f:
        config = toml.loads(f.read())

    # Assign config values to cfg attributes
    for varname in config:
        # Validate attribute names
        if varname in ignoredVarNames or varname not in cfg.__dict__:
            raise NameError("Unrecognised config variable name: " + varname)

        # Load emoji config vars
        elif varname == "defaultEmojis":
            for emojiName in config[varname]:
                # Load emojis
                if emojiName in emojiVars:
                    cfg.defaultEmojis[emojiName] = UninitializedBasedEmoji(config["defaultEmojis"][emojiName])
                # Load lists of emojis
                elif varname in emojiListVars:
                    cfg.defaultEmojis[emojiName] = [UninitializedBasedEmoji(item)
                                                    for item in config["defaultEmojis"][emojiName]]
        else:
            # Get default value for variable
            default = getattr(cfg, varname)
            # Ensure new value is of the correct type
            if type(config[varname]) != type(default):
                try:
                    # Attempt casts for incorrect types - useful for things like ints instead of floats.
                    config[varname] = type(default)(config[varname])
                    print("[WARNING] Casting config variable " + varname + " from " + type(config[varname]).__name__ +
                                                                            " to " + type(default).__name__)
                except Exception:
                    # Where a variable is of the wrong type and cannot be casted, raise an exception.
                    raise TypeError("Unexpected type for config variable " + varname + ": Expected " +
                                    type(default).__name__ + ", received " + type(config[varname]).__name__)

            # Not an emoji and correct type, so set variable.
            else:
                setattr(cfg, varname, config[varname])

    # No errors encountered
    print("Config successfully loaded: " + cfgFile)
