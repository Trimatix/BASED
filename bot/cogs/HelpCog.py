"""https://gist.github.com/Rapptz/0ad5914e42aeaa1cecea334f6508b8d5"""

from __future__ import annotations
from typing import List, Optional, Union, cast
from .. import client
from discord import AppCommandType, CategoryChannel, Embed, VoiceChannel, app_commands, Interaction, Object, ChannelType, Guild
from discord.ext import commands
from discord.app_commands.transformers import CommandParameter, Range
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand


def get_nested_command(bot: client.BasedClient, name: str, guild: Optional[Guild]) -> Optional[Union[app_commands.Command, app_commands.Group]]:
    key, *keys = name.split(' ')
    cmd = bot.tree.get_command(key, guild=guild) or bot.tree.get_command(key)
    for key in keys:
        if cmd is None:
            return None
        if isinstance(cmd, app_commands.Command):
            break
        cmd = cmd.get_command(key)
    return cmd


def formatSignatureParams(command: app_commands.Command) -> str:
        return " ".join(f'**<{param.display_name}>**' if param.required else \
                        f'*[{param.display_name}]*' for param in command._params.values())


def formatChannelType(c: ChannelType) -> str:
        return str(c).replace("_", " ")


def formatSignature(command: app_commands.Command) -> str:
        params = formatSignatureParams(command)
        return f"**{command.qualified_name}**{f' {params}' if params else ''}"


def paramDescription(param: CommandParameter, meta: basedCommand.BasedCommandMeta) -> str:
    return meta.formattedParamDescs.get(param.name, '') \
            or (param.description if param.description != '…' else '')


def paramDescribable(param: CommandParameter, meta: basedCommand.BasedCommandMeta) -> bool:
    return any((paramDescription(param, meta), param.channel_types, param.min_value is not None, param.max_value is not None))


def formatParamRequirements(param: CommandParameter, meta: basedCommand.BasedCommandMeta) -> str:
    base = f"**{param.display_name}**: {paramDescription(param, meta)}"
    rest = ", ".join(i for i in
    (
            "/".join(formatChannelType(t) for t in param.channel_types) + " channel" if param.channel_types else '',
            f"at least {param.min_value}" if param.min_value is not None else '',
            f"at most {param.max_value}" if param.max_value is not None else ''
    ) if i)
    return f"{base} *{rest}*" if rest else base


def formatDescriptionParams(command: app_commands.Command, meta: basedCommand.BasedCommandMeta) -> str:
    return "\n".join(formatParamRequirements(param, meta) for param in command._params.values() if paramDescribable(param, meta))


def commandDescription(command: app_commands.Command, meta: basedCommand.BasedCommandMeta) -> str:
    return meta.formattedDesc or command.description or \
        (command.callback.__doc__ if isinstance(command, app_commands.Command) else command.__doc__)


def commandDescriptionAndParameters(command: app_commands.Command, meta: basedCommand.BasedCommandMeta) -> str:
    params = formatDescriptionParams(command, meta)
    return commandDescription(command, meta) + (f"\n\n{params}" if params else "")


class HelpCog(basedCommand.BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)


    def getCommands(self, interaction: Interaction) -> List[Union[app_commands.Command, app_commands.AppCommandGroup]]:
        foundCommands = list(self.bot.tree.walk_commands(guild=None, type=AppCommandType.chat_input))
        if interaction.guild is not None:
            foundCommands.extend(self.bot.tree.walk_commands(guild=interaction.guild, type=AppCommandType.chat_input))
        return foundCommands


    @basedCommand.command(accessLevel=basicAccessLevels.user)
    @app_commands.command(name="help",
                            description="Look up help for a particular command, or view all available commands.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_help(self, interaction: Interaction, command: Optional[str] = None):
        if command is None:
            count = 1
            
            e = Embed(title=f"{basedCommand.accessLevel(self.cmd_help).name.title()} Commands")
            for c in self.getCommands(interaction):
                if count == 5:
                    break
                meta = basedCommand.commandMeta(command)
                e.add_field(name=formatSignature(c, meta), value=commandDescription(c, meta), inline=False)
                count += 1
            await interaction.response.send_message(embed=e)
            return

        cmd = get_nested_command(self.bot, command, guild=interaction.guild)
        if cmd is None:
            await interaction.response.send_message(f'Could not find a command named {command}', ephemeral=True)
            return

        meta = basedCommand.commandMeta(cmd)
        embed = Embed(title=formatSignature(cmd), description=commandDescriptionAndParameters(cmd, meta))

        await interaction.response.send_message(embed=embed, ephemeral=True)


    @cmd_help.autocomplete('command')
    async def help_autocomplete(self,
        interaction: Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        commandsForScope = self.getCommands(interaction)

        choices: List[app_commands.Choice[str]] = []
        for c in commandsForScope:
            name = c.qualified_name
            if current in name:
                choices.append(app_commands.Choice(name=name, value=name))

        # Only show unique commands
        choices = sorted(set(choices), key=lambda c: c.name)
        return choices[:25]
        

async def setup(bot: client.BasedClient):
    bot.remove_command("help")
    await bot.add_cog(HelpCog(bot), guilds=cfg.developmentGuilds)
