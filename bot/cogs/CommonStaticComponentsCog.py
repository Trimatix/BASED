from discord import Interaction

from .. import client, lib
from ..lib.discordUtil import ZWSP, textChannel
from ..cfg import cfg
from ..interactions.basedApp import BasedCog
from ..interactions.basedComponent import StaticComponents

class CommonStaticComponentsCog(BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)


    @BasedCog.staticComponentCallback(StaticComponents.Clear_View)
    async def clearViewFromMessage(self, interaction: Interaction, args: str):
        if interaction.response.is_done():
            await interaction.edit_original_response(view=None)
        else:
            await interaction.response.edit_message(view=None)


    @BasedCog.staticComponentCallback(StaticComponents.Delete_Message)
    async def deleteMessage(self, interaction: Interaction, args: str):
        await interaction.message.delete() if interaction.message is not None else await interaction.delete_original_response()


    @BasedCog.staticComponentCallback(StaticComponents.Clone_Message)
    async def cloneMessage(self, interaction: Interaction, args: str):
        if args and interaction.user.id != int(args):
            return

        message = interaction.message
        if message is None: return
        embed = message.embeds[0] if message.embeds else None

        await interaction.response.edit_message(content="sent!", view=None)
        if embed is not None:
            if lib.discordUtil.embedEmpty(embed):
                embed.description = ZWSP
            await textChannel(interaction).send(content=message.content, embed=embed)
        else:
            await textChannel(interaction).send(content=message.content)
        await self.clearViewFromMessage(interaction, args)


async def setup(bot: client.BasedClient):
    # TODO: Fix SerializableDiscordObject somehow not matching Snowflake protocol
    await bot.add_cog(CommonStaticComponentsCog(bot),
                        guilds=cfg.developmentGuilds) # type: ignore[reportGeneralTypeIssues]
