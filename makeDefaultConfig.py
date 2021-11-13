import sys
from bot.cfg import cfg
from carica import makeDefaultCfg # type: ignore[import]

# If a file name was provided, pass to config generator
if len(sys.argv) > 1:
    makeDefaultCfg(cfg, fileName=sys.argv[1])
else:
    # Otherwise, generate with default file name
    makeDefaultCfg(cfg)
