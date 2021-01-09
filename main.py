import sys
from bot.cfg.configurator import loadCfg

if len(sys.argv) > 1:
    loadCfg(sys.argv[1])

from bot import bot

status = bot.run()

sys.exit(status)