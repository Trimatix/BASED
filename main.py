import sys
from bot.cfg import cfg
import carica

# Load config if one is given
if len(sys.argv) > 1:
    carica.loadCfg(cfg, sys.argv[1])

# load and run bot
from bot import bot
status = bot.run()

# return exit status code for bot restarting
sys.exit(status)
