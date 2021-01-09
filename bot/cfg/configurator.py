from . import cfg
import toml
import os
from ..lib.emojis import UninitializedBasedEmoji

ignoredVarNames = ("__name__", "__doc__", "__package__", "__loader__", "__spec__", "__file__", "__cached__", "__builtins__", "UninitializedBasedEmoji", "pathVars")
emojiVars = []
emojiListVars = []
for varname, varvalue in vars(cfg).items():
    if type(varvalue) == UninitializedBasedEmoji:
        emojiVars.append(varname)
    elif type(varvalue) == list:
        onlyEmojis = True
        for item in varvalue:
            if type(item) != UninitializedBasedEmoji:
                onlyEmojis = False
                break
        if onlyEmojis:
            emojiListVars.append(varname)


def makeDefaultCfg():
    cfgBase = "defaultCfg"
    cfgPath = "defaultCfg"
    fileExt = ".toml"
    currentExt = 0
    while os.path.exists(cfgPath + fileExt):
        currentExt += 1
        cfgPath = cfgBase + "-" + str(currentExt)

    cfgPath += fileExt

    defaults = {varname: varvalue for varname, varvalue in vars(cfg).items() if varname not in ignoredVarNames}
    for varname in emojiVars:
        defaults[varname] = getattr(cfg, varname).value
    
    for varname in emojiListVars:
        working = []
        for item in defaults[varname]:
            working.append(item.value)
            
        defaults[varname] = working

    with open(cfgPath, "w", encoding="utf-8") as f:
        f.write(toml.dumps(defaults))

def loadCfg(cfgFile : str):
    if not cfgFile.endswith(".toml"):
        raise ValueError("config files must be TOML")

    with open(cfgFile, "r", encoding="utf-8") as f:
        config = toml.loads(f.read())
    
    for varname in config:
        if varname in ignoredVarNames or varname not in cfg.__dict__:
            raise NameError("Unrecognised config variable name: " + varname)
        elif varname in emojiVars:
            setattr(cfg, varname, UninitializedBasedEmoji(config[varname]))
        elif varname in emojiListVars:
            setattr(cfg, varname, [UninitializedBasedEmoji(item) for item in config[varname]])
        else:
            default = getattr(cfg, varname)
            if type(config[varname]) != type(default):
                try:
                    config[varname] = type(default)(config[varname])
                except Exception:
                    raise TypeError("Unexpected type for config variable " + varname + ": Expected " + type(default).__name__ + ", received " + type(config[varname]).__name__)
            else:
                setattr(cfg, varname, config[varname])

    print("Config successfully loaded: " + cfgFile)