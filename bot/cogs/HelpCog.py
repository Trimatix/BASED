"""https://gist.github.com/Rapptz/0ad5914e42aeaa1cecea334f6508b8d5"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Type, Union, cast
from .. import client, lib
from discord import AppCommandType, CategoryChannel, Colour, Embed, InteractionType, VoiceChannel, app_commands, Interaction, Object, ChannelType, Guild
from discord.app_commands import Command
from discord.ext import commands
from discord.app_commands.transformers import CommandParameter, Range
from discord.utils import MISSING
from discord.ui import View, Button
from discord import HTTPException
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from ..interactions import accessLevels, basedCommand, commandChecks, basedApp, basedComponent
from .helpUtil import *


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


def formatSignature(command: Union[app_commands.Command, app_commands.Group]) -> str:
    params = '' if isinstance(command, app_commands.Group) else formatSignatureParams(command)
    return f"**{command.qualified_name}**{f' {params}' if params else ''}"


def paramDescription(param: CommandParameter, meta: basedCommand.BasedCommandMeta) -> str:
    return meta.formattedParamDescs.get(param.name, '') if meta.formattedParamDescs is not None else '' \
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


def commandDescription(command: Union[app_commands.Command, app_commands.Group], meta: basedCommand.BasedCommandMeta) -> str:
    if not meta.formattedDesc:
        d = command.description or \
        (command.callback.__doc__ if isinstance(command, app_commands.Command) else command.__doc__)
        return d if d != "…" and d is not None else "(description missing)"
    return meta.formattedDesc 


def commandDescriptionAndParameters(command: Union[app_commands.Command, app_commands.Group], meta: basedCommand.BasedCommandMeta) -> str:
    params = formatDescriptionParams(command, meta) if isinstance(command, app_commands.Command) else ''
    return commandDescription(command, meta) + (f"\n\n{params}" if params else "")


def packHelpPageArgs(showAll: bool, category: Optional[str] = None, pageNum: Optional[int] = None, accessLevelNum: Optional[int] = None) -> str:
    return HELP_CUSTOMID_ARGS_SEPARATOR.join((
        category or "",
        str(lib.ids.indexToID(pageNum, pad=HELP_CUSTOMID_PAGE_ID_MAX_LENGTH, exclusions=HELP_CUSTOMID_ARGS_SEPARATOR)) if pageNum is not None else "",
        str(lib.ids.indexToID(accessLevelNum, pad=HELP_CUSTOMID_ACCESS_ID_MAX_LENGTH, exclusions=HELP_CUSTOMID_ARGS_SEPARATOR)) if accessLevelNum is not None else "",
        "1" if showAll else ""
    ))


def unpackHelpPageArgs(args: str) -> Tuple[Optional[str], Optional[int], Optional[int], bool]:
    category, pageNum, accessLevelNum, showAll = args.split(HELP_CUSTOMID_ARGS_SEPARATOR)
    return (
        category or None,
        lib.ids.idToIndex(pageNum, exclusions=HELP_CUSTOMID_ARGS_SEPARATOR) if pageNum else None,
        lib.ids.idToIndex(accessLevelNum, exclusions=HELP_CUSTOMID_ARGS_SEPARATOR) if accessLevelNum else None,
        bool(showAll)
    )


class HelpCog(basedApp.BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)


    def _commandsForAccessLevel(self, level: Optional[basedCommand.AccessLevelType] = None, guild: Optional[Union[Object, Guild]] = None, type=AppCommandType.chat_input, exactLevel=True):
        return list(c for c in self.bot.tree.walk_commands(guild=guild, type=type) if isinstance(c, app_commands.Command)) if level is None else \
            [c for c in self.bot.tree.walk_commands(guild=guild, type=type) \
                if isinstance(c, app_commands.Command) and ((basedCommand.accessLevel(c) is level) \
                    if exactLevel else \
                (commandChecks.accessLevelSufficient(level, basedCommand.accessLevel(c))))]


    def getCommands(self, interaction: Interaction, level: Optional[basedCommand.AccessLevelType] = None, exactLevel=True) -> List[app_commands.Command]:
        foundCommands = self._commandsForAccessLevel(level, exactLevel=exactLevel)
        if interaction.guild is not None:
            foundCommands.extend(self._commandsForAccessLevel(level, guild=interaction.guild, exactLevel=exactLevel))
        return foundCommands


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user)
    @app_commands.describe(help_section="Only view commands in a particular help section",
                            command="Only view help for a single command")
    @app_commands.command(name="help",
                            description="Look up help for a particular command or section, or view all available commands.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_help(self, interaction: Interaction, command: Optional[str] = None, help_section: Optional[str] = None):
        if command is None:
            if help_section is None:
                await self.showHelpPageAllSections(interaction, accessLevels.defaultAccessLevel())
            else:
                await self.showHelpPageSingleSection(interaction, accessLevels.defaultAccessLevel(), help_section)
            return

        cmd = get_nested_command(self.bot, command, guild=interaction.guild)
        # TODO: Currently BasedCommand does not support command groups
        if cmd is None or isinstance(cmd, app_commands.Group):
            accessRequired = accessLevels.defaultAccessLevel()
            meta = basedCommand.BasedCommandMeta()
        else:
            accessRequired = basedCommand.accessLevel(cmd)
            meta = basedCommand.commandMeta(cmd)

        if cmd is None or not await commandChecks.userHasAccess(interaction, accessRequired):
            await interaction.response.send_message(f'{cfg.defaultEmojis.cancel} Unknown command: `{command}`.', ephemeral=True)
            return

        embed = Embed(title=formatSignature(cmd), description=commandDescriptionAndParameters(cmd, meta), colour=Colour.blue())

        await interaction.response.send_message(embed=embed, ephemeral=True)


    @cmd_help.autocomplete('command')
    async def help_autocomplete(self,
        interaction: Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        commandsForScope = self.getCommands(interaction, await commandChecks.inferUserPermissions(interaction), exactLevel=False)

        choices: List[app_commands.Choice[str]] = []
        for c in commandsForScope:
            name = c.qualified_name
            if current in name:
                choices.append(app_commands.Choice(name=name, value=name))

        # Only show unique commands
        choices = sorted(set(choices), key=lambda c: c.name)
        return choices[:25]


    @cmd_help.autocomplete('help_section')
    async def helpSection_autocomplete(self,
        interaction: Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return [app_commands.Choice(name=c, value=c) for c in self.bot.helpSections if current in c][:25]


    @basedApp.BasedCog.staticComponentCallback(basedComponent.StaticComponents.Help)
    async def showHelpPageStatic(self, interaction: Interaction, args: str):
        category, page, accessLevelNum, showAll = unpackHelpPageArgs(args)
        pageNum = int(page) if page is not None else 1
        commandAccessLevel = accessLevels.defaultAccessLevel() if accessLevelNum is None else accessLevels.accessLevelWithIntLevel(accessLevelNum)
        if showAll or category is None:
            await self.showHelpPageAllSections(interaction, commandAccessLevel, category=category, pageNum=pageNum)
        else:
            await self.showHelpPageSingleSection(interaction, commandAccessLevel, category, pageNum=pageNum)


    async def showHelpPageAllSections(self, interaction: Interaction, commandAccessLevel: basedCommand.AccessLevelType, category: Optional[str] = None, pageNum: Optional[int] = None, helpSections: Optional[Dict[str, List[app_commands.Command]]] = None):
        # This method calls itself sometimes. The helpSections argument acts as a cache, so we don't keep having to look up potential commands.
        helpSections = helpSections if helpSections is not None else self.bot.helpSectionsForAccessLevel(commandAccessLevel)
        
        # If no commands are available in the current section for the access level, show an empty list
        if not helpSections:
            helpSections = {cfg.defaultHelpSection: []}
        helpSectionNames = list(helpSections.keys())

        if category is None:
            await self.showHelpPageAllSections(interaction, category=helpSectionNames[0], pageNum=1, commandAccessLevel=commandAccessLevel, helpSections=helpSections)
            return

        # This will happen if the user clicks the 'back' button when on the first page of a help section, to go back to the last help section
        if pageNum == 0:
            await self.showHelpPageAllSections(interaction, category=helpSectionNames[helpSectionNames.index(category) - 1], pageNum=1, commandAccessLevel=commandAccessLevel, helpSections=helpSections)
            return

        # This will happen if the user is browsing a particular help section and then changes access level to a level that does not have commands in the section
        if category not in helpSections:
            category = helpSectionNames[0]

        pageNum = pageNum or 1
            
        offset = cfg.maxCommandsPerHelpPage * (pageNum - 1)
        possibleCommands = self.bot.commandsInSectionForAccessLevel(category, commandAccessLevel)

        # This will happen if the user clicks the 'next' button when on the last page of a help section, to go to the next help section
        if offset > len(possibleCommands):
            nextSection = helpSectionNames[helpSectionNames.index(category) + 1]
            await self.showHelpPageAllSections(interaction, category=nextSection, pageNum=1, commandAccessLevel=commandAccessLevel, helpSections=helpSections)
            return

        defaultAccessLevel = accessLevels.defaultAccessLevel()
        userAccessLevel = await commandChecks.inferUserPermissions(interaction)

        # Find all access levels the user can switch to
        if userAccessLevel is defaultAccessLevel:
            switchableAccessLevels = []
        else:
            switchableAccessLevels = [accessLevels.accessLevelWithIntLevel(l) for l in range(defaultAccessLevel._intLevel(), userAccessLevel._intLevel() + 1)]

        e = Embed(description=cfg.helpIntro)

        if switchableAccessLevels:
            e.description = (e.description or "") + f"\n{cfg.defaultEmojis.spiral}: Change access level"

        if len(helpSections) > 1:
            e.description = (e.description or "") + "\n\n" + " / ".join(f"__{section.title()}__" if section == category else section.title() for section in helpSectionNames)
        else:
            e.description = (e.description or "") + f"\n\n__{category.title()}__"
        
        notFirstPage = offset != 0 or category != helpSectionNames[0]
        last = min(len(possibleCommands), offset + cfg.maxCommandsPerHelpPage)
        notLastInSection = last != len(possibleCommands)
        notLastPage = notLastInSection or category != helpSectionNames[-1]

        await self.fillAndSendHelpPage(interaction, True, e, category, pageNum, commandAccessLevel, notLastInSection, possibleCommands, offset, last, notFirstPage, notLastPage, switchableAccessLevels, userAccessLevel)

    
    async def showHelpPageSingleSection(self, interaction: Interaction, commandAccessLevel: basedCommand.AccessLevelType, category: str, pageNum: Optional[int] = None):
        userAccessLevel = await commandChecks.inferUserPermissions(interaction)

        if category not in self.bot.helpSections:
            pageNum = 1
            offset = 0
            possibleCommands = []
            switchableAccessLevels = []
        else:
            defaultAccessLevel = accessLevels.defaultAccessLevel()

            pageNum = pageNum or 1
            offset = cfg.maxCommandsPerHelpPage * (pageNum - 1)
            possibleCommands = self.bot.commandsInSectionForAccessLevel(category, commandAccessLevel)
            switchableAccessLevels = []
            
            # Find all access levels the user can switch to and still have commands available in the section
            if userAccessLevel is not defaultAccessLevel:
                noCommands = not possibleCommands
                for l in range(defaultAccessLevel._intLevel(), userAccessLevel._intLevel() + (userAccessLevel is not commandAccessLevel)):
                    if l == commandAccessLevel._intLevel():
                        continue
                    level = accessLevels.accessLevelWithIntLevel(l)
                    # This will happen if a help section is requested that only contains commands at an access level higher than the default
                    # Pick the lowest access level that the user has access to and also contains commands in this section
                    if noCommands:
                        currentCommands = self.bot.commandsInSectionForAccessLevel(category, level)
                        if currentCommands:
                            possibleCommands = currentCommands
                            commandAccessLevel = level
                            noCommands = False
                    # Once we're sure we've got an access level with some commands, we can do a more efficient lookup
                    # that exits checking a given level as soon as a single matching command is found
                    elif any(basedCommand.accessLevel(c) is level for c in self.bot.helpSections[category]):
                        switchableAccessLevels.append(level)

        e = Embed(description=cfg.helpIntro)
        if switchableAccessLevels:
            e.description = (e.description or "") + f"\n{cfg.defaultEmojis.spiral}: Change access level"
        e.description = (e.description or "") + f"\n\n__{category.title()}__"

        notFirstPage = offset != 0
        last = min(len(possibleCommands), offset + cfg.maxCommandsPerHelpPage)
        notLastInSection = last != len(possibleCommands)
        notLastPage = notLastInSection

        await self.fillAndSendHelpPage(interaction, False, e, category, pageNum, commandAccessLevel, notLastInSection, possibleCommands, offset, last, notFirstPage, notLastPage, switchableAccessLevels, userAccessLevel)


    async def fillAndSendHelpPage(self, interaction: Interaction, showAll: bool, embed: Embed, category: str, pageNum: int, commandAccessLevel: basedCommand.AccessLevelType, notLastInSection: bool, possibleCommands: List[app_commands.Command], offset: int, last: int, notFirstPage: bool, notLastPage: bool, switchableAccessLevels: List[basedCommand.AccessLevelType], userAccessLevel: basedCommand.AccessLevelType):
        embed.title = f"{commandAccessLevel.name.title()} Commands"
        embed.colour = Colour.blue()

        if notLastInSection:
            embed.set_footer(text=f"Page {pageNum}")

        # Fill the embed fields with the found commands
        if not possibleCommands:
            embed.description = (embed.description or "") + "\n\n<no commands>"
        else:
            for c in possibleCommands[offset:last]:
                meta = basedCommand.commandMeta(c)
                embed.add_field(name=formatSignature(c), value=commandDescription(c, meta), inline=False)

        # If we need to add any buttons
        if notFirstPage or notLastPage or switchableAccessLevels:
            view = View()
            previousPageButton = Button(emoji=cfg.defaultEmojis.previous.sendable, disabled=True)
            nextPageButton = Button(emoji=cfg.defaultEmojis.next.sendable, disabled=True)

            # Circle access level switch around from bottom to top
            if switchableAccessLevels:
                if len(switchableAccessLevels) == 1:
                    nextAccessLevel = switchableAccessLevels[0]
                else:
                    nextAccessLevel = None
                    minAccessLevel = switchableAccessLevels[0]
                    for c in switchableAccessLevels[1:]:
                        if c._intLevel() > commandAccessLevel._intLevel():
                            nextAccessLevel = c
                            break
                        if c._intLevel() < minAccessLevel._intLevel():
                            minAccessLevel = c
                    
                    if nextAccessLevel is None:
                        nextAccessLevel = minAccessLevel

                switchAccessLevelButton = Button(emoji=cfg.defaultEmojis.spiral.sendable)
                # Setting category to None, so that the first category is shown
                switchAccessLevelButton = basedComponent.StaticComponents.Help(switchAccessLevelButton, args=packHelpPageArgs(showAll, accessLevelNum=nextAccessLevel._intLevel(), category=None))
                view.add_item(switchAccessLevelButton)

            # Add 'back' and 'next' buttons
            if notFirstPage:
                previousPageButton = basedComponent.StaticComponents.Help(previousPageButton, args=packHelpPageArgs(showAll, pageNum=pageNum-1, accessLevelNum=commandAccessLevel._intLevel(), category=category))
                previousPageButton.disabled = False
            if notLastPage:
                nextPageButton = basedComponent.StaticComponents.Help(nextPageButton, args=packHelpPageArgs(showAll, pageNum=min(HELP_MAX_PAGE, pageNum+1), accessLevelNum=commandAccessLevel._intLevel(), category=category))
                nextPageButton.disabled = False

            view.add_item(previousPageButton).add_item(nextPageButton)
        else:
            view = MISSING
        
        if interaction.type == InteractionType.component:
            if interaction.response._responded:
                await interaction.edit_original_message(embed=embed, view=view)
            else:
                # TODO: I'm not sure why I keep getting 'interaction already acknowledged' here. The interaction should be new for each button press?
                try:
                    await interaction.response.edit_message(embed=embed, view=view)
                except HTTPException:
                    pass
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: client.BasedClient):
    bot.remove_command("help")
    await bot.add_cog(HelpCog(bot), guilds=cfg.developmentGuilds)
