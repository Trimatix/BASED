import sys
from bot.cfg.configurator import makeDefaultCfg

# If a file name was provided, pass to config generator
if len(sys.argv) > 1:
    makeDefaultCfg(fileName=sys.argv[1])
else:
    # Otherwise, generate with default file name
    makeDefaultCfg()
