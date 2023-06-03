import sys
from bot.cfg import cfg
import carica # type: ignore[import]

# Load config if one is given
if len(sys.argv) > 1:
    carica.loadCfg(cfg, sys.argv[1])

cfg.validateConfig()

# load and run bot
from bot import bot
status = bot.run()

# return exit status code for bot restarting
sys.exit(status.value)
