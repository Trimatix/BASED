import sys
from bot.cfg.configurator import makeDefaultCfg

if len(sys.argv) > 1:
    makeDefaultCfg(fileName=sys.argv[1])
else:
    makeDefaultCfg()