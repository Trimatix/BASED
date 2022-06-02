from .. import client
from discord import Interaction
from ..cfg import cfg
from ..interactions.basedApp import BasedCog
from ..interactions.basedComponent import StaticComponents

class CommonStaticComponentsCog(BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)


    @BasedCog.staticComponentCallback(StaticComponents.Clear_View)
    async def cancel(self, interaction: Interaction):
        await interaction.response.edit_message(view=None)


async def setup(bot: client.BasedClient):
    await bot.add_cog(CommonStaticComponentsCog(bot), guilds=cfg.developmentGuilds)
