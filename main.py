import sys
import bot
from bot.cfg.configurator import loadCfg

if len(sys.argv) > 1:
    loadCfg(sys.argv[1])

status = bot.bot.run()

sys.exit(status)