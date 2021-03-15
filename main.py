import sys
from bot.cfg import configurator

# Load config if one is given
if len(sys.argv) > 1:
    configurator.loadCfg(sys.argv[1])

# initialize bot config
configurator.init()

# load and run bot
from bot import bot
status = bot.run()

# return exit status code for bot restarting
sys.exit(status)
