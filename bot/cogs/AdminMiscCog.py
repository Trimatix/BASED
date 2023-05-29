from time import perf_counter

from discord import app_commands, Interaction

from .. import client
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand, basedApp


class AdminMiscCog(basedApp.BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin)
    @app_commands.command(name="ping",
                            description="Measure the latency between the bot sending a message, and receiving a response from discord.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def admin_cmd_ping(self, interaction: Interaction):
        """admin command testing bot latency.

        :param discord.Message message: the discord message calling the command
        :param str args: ignored
        :param bool isDM: Whether or not the command is being called from a DM channel
        """
        start = perf_counter()
        await interaction.response.send_message("Ping...")
        end = perf_counter()
        duration = (end - start) * 1000
        msg = await interaction.original_response()
        await msg.edit(content='Pong! {:.2f}ms'.format(duration))


async def setup(bot: client.BasedClient):
    await bot.add_cog(AdminMiscCog(bot), guilds=cfg.developmentGuilds) # type: ignore[reportGeneralTypeIssues]
