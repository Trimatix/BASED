"""https://gist.github.com/Rapptz/0ad5914e42aeaa1cecea334f6508b8d5"""

from __future__ import annotations
from typing import List, Optional, Tuple, Type, Union, cast
from .. import client
from discord import AppCommandType, CategoryChannel, Embed, VoiceChannel, app_commands, Interaction, Object, ChannelType, Guild
from discord.ext import commands
from discord.app_commands.transformers import CommandParameter, Range
from discord.utils import MISSING
from discord.ui import View, Button
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand, accessLevel, commandChecks, basedApp, basedComponent


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


def packHelpPageArgs(category: str = None, pageNum: int = None, accessLevelNum: int = None) -> str:
    return "#".join((category or "", str(pageNum) if pageNum is not None else "", str(accessLevelNum) if accessLevelNum is not None else ""))


def unpackHelpPageArgs(args: str) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    category, pageNum, accessLevelNum = args.split("#")
    return (category or None, int(pageNum) if pageNum else None, int(accessLevelNum) if accessLevelNum else None)


class HelpCog(basedApp.BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)


    def _commandsForAccessLevel(self, level: Type[accessLevel._AccessLevelBase] = MISSING, guild: Optional[Object] = None, type=AppCommandType.chat_input):
        return list(self.bot.tree.walk_commands(guild=guild, type=type)) if level is None else \
            [c for c in self.bot.tree.walk_commands(guild=guild, type=type) if basedCommand.accessLevel(c) is level]


    def getCommands(self, interaction: Interaction, level: Optional[Type[basedCommand.AccessLevel]] = None) -> List[Union[app_commands.Command, app_commands.AppCommandGroup]]:
        foundCommands = self._commandsForAccessLevel(level)
        if interaction.guild is not None:
            foundCommands.extend(self._commandsForAccessLevel(level, guild=interaction.guild))
        return foundCommands


    @basedCommand.command(accessLevel=basicAccessLevels.user)
    @app_commands.command(name="help",
                            description="Look up help for a particular command, or view all available commands.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_help(self, interaction: Interaction, command: Optional[str] = None):
        if command is None:
            await self.showHelpPage(interaction, packHelpPageArgs())
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
        commandsForScope = self.getCommands(interaction, await commandChecks.inferUserPermissions(interaction))

        choices: List[app_commands.Choice[str]] = []
        for c in commandsForScope:
            name = c.qualified_name
            if current in name:
                choices.append(app_commands.Choice(name=name, value=name))

        # Only show unique commands
        choices = sorted(set(choices), key=lambda c: c.name)
        return choices[:25]


    @basedComponent.staticComponentCallback(category="help")
    async def showHelpPage(self, interaction: Interaction, args: str):
        category, page, accessLevelNum = unpackHelpPageArgs(args)
        pageNum = int(page) if page is not None else 1
        commandAccessLevel = accessLevel.defaultAccessLevel() if accessLevelNum is None else accessLevel.accessLevelWithIntLevel(accessLevelNum)

        offset = cfg.maxCommandsPerHelpPage * (pageNum - 1)
            
        e = Embed(title=f"{commandAccessLevel.name.title()} Commands")
        e.set_footer(text=f"Page {pageNum}")

        possibleCommands = self.getCommands(interaction, level=commandAccessLevel)
        last = min(len(possibleCommands), offset + cfg.maxCommandsPerHelpPage)

        for c in possibleCommands[offset:last]:
            meta = basedCommand.commandMeta(c)
            e.add_field(name=formatSignature(c), value=commandDescription(c, meta), inline=False)

        notFirstPage = offset != 0
        notLastPage = last != len(possibleCommands)

        userAccessLevel = await commandChecks.inferUserPermissions(interaction)
        userNotMinAccessLevel = userAccessLevel is not accessLevel.defaultAccessLevel()
        if notFirstPage or notLastPage or userNotMinAccessLevel:
            view = View()
            previousPageButton = Button(emoji=cfg.defaultEmojis.previous.sendable, disabled=True)
            nextPageButton = Button(emoji=cfg.defaultEmojis.next.sendable, disabled=True)

            if userNotMinAccessLevel:
                if commandAccessLevel is userAccessLevel:
                    nextAccessLevel = 0
                else:
                    nextAccessLevel = commandAccessLevel._intLevel() + 1

                switchAccessLevelButton = Button(emoji=cfg.defaultEmojis.spiral.sendable)
                switchAccessLevelButton = basedComponent.staticComponent(switchAccessLevelButton, "help", args=packHelpPageArgs(accessLevelNum=nextAccessLevel))
                view.add_item(switchAccessLevelButton)

            if notFirstPage:
                previousPageButton = basedComponent.staticComponent(previousPageButton, "help", args=packHelpPageArgs(pageNum=pageNum-1, accessLevelNum=commandAccessLevel._intLevel(), category=category))
                previousPageButton.disabled = False
            if notLastPage:
                nextPageButton = basedComponent.staticComponent(nextPageButton, "help", args=packHelpPageArgs(pageNum=pageNum+1, accessLevelNum=commandAccessLevel._intLevel(), category=category))
                nextPageButton.disabled = False

            view.add_item(previousPageButton).add_item(nextPageButton)
        else:
            view = MISSING
            
        await interaction.response.send_message(embed=e, view=view, ephemeral=True)

    
    @app_commands.command(name="dummy1")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_dummy1(self, interaction: Interaction): pass

    @app_commands.command(name="dummy2")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_dummy2(self, interaction: Interaction): pass

    @app_commands.command(name="dummy3")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_dummy3(self, interaction: Interaction): pass

    @app_commands.command(name="dummy4")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_dummy4(self, interaction: Interaction): pass

    @app_commands.command(name="dummy5")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_dummy5(self, interaction: Interaction): pass

    @app_commands.command(name="dummy6")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_dummy6(self, interaction: Interaction): pass

    @app_commands.command(name="dummy7")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_dummy7(self, interaction: Interaction): pass

    @app_commands.command(name="dummy8")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_dummy8(self, interaction: Interaction): pass

    @app_commands.command(name="dummy9")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_dummy9(self, interaction: Interaction): pass

    @app_commands.command(name="dummy10")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_dummy10(self, interaction: Interaction): pass
        

async def setup(bot: client.BasedClient):
    bot.remove_command("help")
    await bot.add_cog(HelpCog(bot), guilds=cfg.developmentGuilds)
