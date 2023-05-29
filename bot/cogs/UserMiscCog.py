import discord
from discord import app_commands, Interaction, Colour
from discord.utils import utcnow

from .. import client, lib
from ..lib.BASED_version import getBASEDVersion, BASED_REPO_URL
from ..cfg import cfg
from ..interactions import basedCommand, basedApp


class UserMiscCog(basedApp.BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)


    @basedCommand.basedCommand()
    @app_commands.command(name="source",
                            description="Get information about the bot, including a link to source code.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_source(self, interaction: Interaction):
        """Print a short message with information about the bot's source code.
        """
        srcEmbed = lib.discordUtil.makeEmbed(authorName="Source Code",
                                            col=Colour.purple(),
                                            icon="https://image.flaticon.com/icons/png/512/25/25231.png",
                                            footerTxt="Bot Source",
                                            footerIcon="https://i.imgur.com/7SMgF0t.png")
        srcEmbed.add_field(name="Uptime",
                            value=lib.timeUtil.td_format_noYM(utcnow() - self.bot.launchTime))
        srcEmbed.add_field(name="Author",
                            value="Trimatix#2244")
        srcEmbed.add_field(name="Library",
                            value="[Discord.py " + discord.__version__ + "](https://github.com/Rapptz/discord.py/)")
        srcEmbed.add_field(name="BASED",
                                value=f"[BASED {getBASEDVersion().BASED_version}]({BASED_REPO_URL})")
        srcEmbed.add_field(name="GitHub",
                            value="Please ask the bot developer to post their GitHub repository here!")
        srcEmbed.add_field(name="Invite",
                            value="Please ask the bot developer to post the bot's invite link here!")
        await interaction.response.send_message(embed=srcEmbed)


async def setup(bot: client.BasedClient):
    await bot.add_cog(UserMiscCog(bot), guilds=cfg.developmentGuilds) # type: ignore[reportGeneralTypeIssues]
