from typing import cast
from .. import client
from discord import AppCommandType, Embed, app_commands, Interaction, Object, ChannelType
from discord.ext import commands
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand


class HelpCog(basedCommand.BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)


    @basedCommand.command(accessLevel=basicAccessLevels.user)
    @app_commands.command(name="help",
                            description="Look up help for a particular command, or view all available commands.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_help(self, interaction: Interaction):
        guildId = None if interaction.channel.type == ChannelType.private else Object(interaction.guild_id)
        count = 1
        
        e = Embed(title=f"{self.bot.accessLevel(self.cmd_help).name.title()} Commands")
        for command in self.bot.tree.walk_commands(guild=guildId, type=AppCommandType.chat_input):
            if count == 5:
                break
            e.add_field(name=command.name, value=command.description)
            count += 1
        await interaction.response.send_message(embed=e)



async def setup(bot: client.BasedClient):
    bot.remove_command("help")
    await bot.add_cog(HelpCog(bot), guilds=cfg.developmentGuilds)
