import traceback
from typing import List, Optional, TYPE_CHECKING, Protocol, Union
from .. import client, lib
from ..lib.discordUtil import ZWSP, EMPTY_IMAGE, textChannel
import discord
from discord import ComponentType, Message, app_commands, Interaction, ButtonStyle, Embed, TextStyle, Colour, SelectOption
from discord import HTTPException, ClientException, NotFound
from discord.utils import utcnow, MISSING
from discord.ui import View, Modal, TextInput, Button, Select
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from ..interactions.basedComponent import StaticComponents, staticComponentCustomId
from ..logging import LogCategory

EMBED_FIELD_INLINE_DEFAULT = "y"


# I can't get this imported from discord, so I copy-pasted it.
class _EmbedFieldProxy(Protocol):
    name: Optional[str]
    value: Optional[str]
    inline: bool


class EmbedTextParams(Modal):
    authorName = TextInput(label="Author name", required=False, max_length=256)
    titleTxt = TextInput(label="Title", required=False, max_length=256)
    desc = TextInput(label="Description", required=False, style=TextStyle.paragraph, max_length=4000)
    footerText = TextInput(label="Footer text", required=False, max_length=2048)
    colour = TextInput(label="Colour (hex or RANDOM)", required=False, max_length=8)
    
    def __init__(self, *, title: str = MISSING, timeout: Optional[float] = None, custom_id: str = MISSING,
                    currentEmbed: Optional[Embed] = None):
        super().__init__(title=title, timeout=timeout, custom_id=custom_id)
        if currentEmbed is not None:
            self.titleTxt.default = currentEmbed.title or ""
            self.authorName.default = (currentEmbed.author.name or "") if currentEmbed.author is not None else ""
            self.desc.default = currentEmbed.description or ""
            self.footerText.default = (currentEmbed.footer.text or "") if currentEmbed.footer is not None else ""
            self.colour.default = hex(currentEmbed.colour.value) if currentEmbed.colour is not None else ""

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.defer(thinking=False)


class EmbedImageParams(Modal):
    authorIcon = TextInput(label="Author icon", required=False, max_length=4000)
    thumb = TextInput(label="Thumbnail", required=False, max_length=4000)
    img = TextInput(label="Image", required=False, max_length=4000)
    footerIcon = TextInput(label="Footer icon", required=False, max_length=4000)
    
    def __init__(self, *, title: str = MISSING, timeout: Optional[float] = None, custom_id: str = MISSING,
                    currentEmbed: Optional[Embed] = None):
        super().__init__(title=title, timeout=timeout, custom_id=custom_id)
        if currentEmbed is not None:
            self.authorIcon.default = (currentEmbed.author.icon_url or "") if currentEmbed.author is not None else ""
            self.thumb.default = (currentEmbed.thumbnail.url or "") if currentEmbed.thumbnail is not None else ""
            self.img.default = (currentEmbed.image.url or "") if currentEmbed.image is not None else ""
            self.footerIcon.default = (currentEmbed.footer.icon_url or "") if currentEmbed.footer is not None else ""
    
    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.defer(thinking=False)


class EmbedFieldParams(Modal):
    fieldName = TextInput(label="Feld name", required=False)
    fieldValue = TextInput(label="Field value", required=False, style=TextStyle.paragraph)
    fieldInline = TextInput(label="Inline? (y/n)", required=False, max_length=1, placeholder=EMBED_FIELD_INLINE_DEFAULT)

    def __init__(self, *, title: str = MISSING, timeout: Optional[float] = None, custom_id: str = MISSING,
                        currentField: Optional[_EmbedFieldProxy] = None) -> None:
        super().__init__(title=title, timeout=timeout, custom_id=custom_id)
        if currentField is not None:
            self.fieldName.default = currentField.name if currentField.name != ZWSP else ""
            self.fieldValue.default = currentField.value if currentField.value != ZWSP else ""
            self.fieldInline.default = "y" if currentField.inline else "n"
    
    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.defer(thinking=False)


def messageEditorView(userId: Optional[Union[int, str]], embed: Optional[Embed] = None) -> View:
    view = View()
    _userId = "" if userId is None else str(userId)

    confirmButton = Button(style=ButtonStyle.green, label="send", row=0 if embed is None else 2)
    confirmButton = StaticComponents.Clone_Message(confirmButton, args=_userId)
    cancelButton = Button(style=ButtonStyle.red, label="cancel", row=0 if embed is None else 2)
    cancelButton = StaticComponents.Clear_View(cancelButton, args=_userId)
    view.add_item(cancelButton).add_item(confirmButton)
    if embed is not None:
        editEmbedTextButton = Button(style=ButtonStyle.blurple, label="edit embed text", row=0)
        editEmbedTextButton = StaticComponents.User_Embed_Edit_Text(editEmbedTextButton, args=_userId)
        view.add_item(editEmbedTextButton)

        editEmbedImagesButton = Button(style=ButtonStyle.blurple, label="edit embed images", row=0)
        editEmbedImagesButton = StaticComponents.User_Embed_Edit_Images(editEmbedImagesButton, args=_userId)
        view.add_item(editEmbedImagesButton)

        addFieldButton = Button(style=ButtonStyle.blurple, label="add embed field", row=1)
        addFieldButton = StaticComponents.User_Embed_Add_Field(addFieldButton, args=_userId)
        view.add_item(addFieldButton)

        removeFieldButton = Button(style=ButtonStyle.blurple, label="remove embed field", row=1)
        removeFieldButton = StaticComponents.User_Embed_Remove_Field_Select(removeFieldButton, args=_userId)
        view.add_item(removeFieldButton)

        editFieldButton = Button(style=ButtonStyle.blurple, label="edit embed field", row=1)
        editFieldButton = StaticComponents.User_Embed_Edit_Field_Select(editFieldButton, args=_userId)
        view.add_item(editFieldButton)
    
    return view


def interactionErrorString(interaction: Interaction, staticComponentId: StaticComponents) -> str:
    return f"static component {'None' if interaction.data is None else interaction.data.get('custom_id', None)} ({staticComponentId.name}), " \
            f"interaction {interaction.id}, " \
            f"type {interaction.type}, " \
            f"user {interaction.user.name if interaction.user is not None else None} " \
                f"({interaction.user.id if interaction.user is not None else None})"


class DevMiscCog(BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)

#region util

    async def messageForInteraction(self, interaction: Interaction, funcName: str, staticComponentId: StaticComponents) -> Optional[Message]:
        """TODO: This appears to acknowledge the interaction, event """
        if interaction.message is not None: return interaction.message
        # await interaction.response.defer(thinking=False)
        try:
            message = await interaction.original_message()
        except (HTTPException, ClientException, NotFound) as e:
            self.bot.logger.log(type(self).__name__, funcName,
                                "on-message static component triggered for non-message-based interaction: " \
                                    + interactionErrorString(interaction, staticComponentId),
                                category=LogCategory.staticComponents, eventType="MESSAGE_FETCH_FAIL", exception=e)
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " This type of interaction is not valid here.", ephemeral=True)
            return None

        if not message.embeds:
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " The message has no embed!", ephemeral=True)
            return None
        
        return message

#endregion
#region static components

    @BasedCog.staticComponentCallback(StaticComponents.User_Embed_Add_Field)
    async def addField(self, interaction: Interaction, userId: str, *_):
        if userId and interaction.user.id != int(userId):
            return

        message = await self.messageForInteraction(interaction, "addField", StaticComponents.User_Embed_Add_Field)
        if message is None: return
        embed = message.embeds[0]

        if len(embed.fields) == 25:
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " Maximum number of fields reached. Please remove one, or edit an existing field.", ephemeral=True)
            return

        modal = EmbedFieldParams(title="Field Parameters")

        await interaction.response.send_modal(modal)
        if await modal.wait(): return
        
        embed.add_field(name=modal.fieldName.value or ZWSP, value=modal.fieldValue.value or ZWSP, inline=(modal.fieldInline.value or EMBED_FIELD_INLINE_DEFAULT).lower() == "y")
        await interaction.edit_original_message(embed=embed)


    @BasedCog.staticComponentCallback(StaticComponents.User_Embed_Remove_Field_Select)
    async def startRemoveField(self, interaction: Interaction, userId: str, *_):
        if userId and interaction.user.id != int(userId):
            return

        message = await self.messageForInteraction(interaction, "startRemoveField", StaticComponents.User_Embed_Remove_Field_Select)
        if message is None: return
        embed = message.embeds[0]

        if not embed.fields:
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " The embed has no fields!", ephemeral=True)
            return

        view = messageEditorView(userId, embed=embed)

        for c in view.children:
            if isinstance(c, Button):
                c.disabled = True

        fieldSelector = Select(options=[SelectOption(label=f"{i + 1}. {field.name}", value=str(i)) for i, field in enumerate(embed.fields)], max_values=min(len(embed.fields), 25))
        fieldSelector = StaticComponents.User_Embed_Remove_Field(fieldSelector, args=userId)
        view.add_item(fieldSelector)

        await interaction.response.edit_message(view=view)


    @BasedCog.staticComponentCallback(StaticComponents.User_Embed_Remove_Field)
    async def endRemoveField(self, interaction: Interaction, userId: str, *_):
        if userId and interaction.user.id != int(userId):
            return

        message = await self.messageForInteraction(interaction, "endRemoveField", StaticComponents.User_Embed_Remove_Field)
        if message is None: return
        embed = message.embeds[0]

        view = messageEditorView(userId, embed=embed)
        selected: Optional[List[str]] = None if interaction.data is None else interaction.data.get("values", None)

        if not embed.fields:
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " The embed has no fields!", ephemeral=True)
        elif not selected:
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " This type of interaction is not valid here.", ephemeral=True)
            self.bot.logger.log(type(self).__name__, "endRemoveField",
                                "select-based static component triggered for non-select interaction: " \
                                    + interactionErrorString(interaction, StaticComponents.User_Embed_Remove_Field),
                                category=LogCategory.staticComponents, eventType="COMPONENT_NOT_SELECT")
        else:
            selectedFieldIndices = sorted([int(i) for i in selected], reverse=True)
            for i in selectedFieldIndices:
                embed.remove_field(i)

        if lib.discordUtil.embedEmpty(embed):
            embed.description = ZWSP
                
        await interaction.response.edit_message(embed=embed, view=view)


    @BasedCog.staticComponentCallback(StaticComponents.User_Embed_Edit_Field_Select)
    async def startEditField(self, interaction: Interaction, userId: str, *_):
        if userId and interaction.user.id != int(userId):
            return

        message = await self.messageForInteraction(interaction, "startEditField", StaticComponents.User_Embed_Edit_Field_Select)
        if message is None: return
        embed = message.embeds[0]

        view = messageEditorView(userId, embed=embed)

        if not embed.fields:
            await interaction.response.send_message("The embed has no fields!", ephemeral=True)
            return

        for c in view.children:
            if isinstance(c, Button):
                c.disabled = True

        fieldSelector = Select(options=[SelectOption(label=f"{i + 1}. {field.name}", value=str(i)) for i, field in enumerate(embed.fields)], max_values=1)

        fieldSelector = StaticComponents.User_Embed_Edit_Field(fieldSelector, args=userId)
        view.add_item(fieldSelector)

        await interaction.response.edit_message(view=view)

    
    @BasedCog.staticComponentCallback(StaticComponents.User_Embed_Edit_Field)
    async def endEditField(self, interaction: Interaction, userId: str, *_):
        if userId and interaction.user.id != int(userId):
            return

        message = await self.messageForInteraction(interaction, "endEditField", StaticComponents.User_Embed_Edit_Field)
        if message is None: return
        embed = message.embeds[0]

        view = messageEditorView(userId, embed=embed)
        selected: List[str] = [] if interaction.data is None else interaction.data.get("values", [])

        if not embed.fields:
            await interaction.response.send_message("The embed has no fields!", ephemeral=True)
        elif len(selected) != 1:
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " This type of interaction is not valid here.", ephemeral=True)
            self.bot.logger.log(type(self).__name__, "endEditField",
                                "select-based static component triggered for non-select interaction: " \
                                    + interactionErrorString(interaction, StaticComponents.User_Embed_Edit_Field),
                                category=LogCategory.staticComponents, eventType="COMPONENT_NOT_SELECT")
        else:
            selectedFieldIndex = int(selected[0])
            field = embed.fields[selectedFieldIndex]
            
            modal = EmbedFieldParams(title="Field Parameters")
            if field.name != ZWSP:
                modal.fieldName.default = field.name
            if field.value != ZWSP:
                modal.fieldValue.default = field.value
            modal.fieldInline.default = "y" if field.inline else "n"

            await interaction.response.send_modal(modal)
            if await modal.wait(): view.stop()
        
            embed.set_field_at(selectedFieldIndex, name=modal.fieldName.value or ZWSP, value=modal.fieldValue.value or ZWSP, inline=(modal.fieldInline.value or EMBED_FIELD_INLINE_DEFAULT).lower() == "y")

        await interaction.edit_original_message(embed=embed, view=view)


    @BasedCog.staticComponentCallback(StaticComponents.User_Embed_Edit_Text)
    async def editEmbedText(self, interaction: Interaction, userId: str, *_):
        if userId and interaction.user.id != int(userId):
            return

        message = await self.messageForInteraction(interaction, "editEmbedText", StaticComponents.User_Embed_Edit_Text)
        if message is None: return
        embed = message.embeds[0]

        modal = EmbedTextParams(title="Embed Parameters", currentEmbed=embed)

        await interaction.response.send_modal(modal)
        if await modal.wait(): return
        
        if modal.titleTxt.value:
            embed.title = modal.titleTxt.value
        else:
            embed.title = None
            
        authorIcon = (embed.author.icon_url or "") if embed.author is not None else ""
        if modal.authorName.value:
            embed.set_author(name=modal.authorName.value, icon_url=authorIcon or None)
        else:
            if authorIcon:
                embed.set_author(name=ZWSP, icon_url=authorIcon)
            else:
                embed.remove_author()

        if modal.desc.value:
            embed.description = modal.desc.value
        else:
            embed.description = None

        footerIcon = (embed.footer.icon_url or "") if embed.footer is not None else ""
        if modal.footerText.value:
            embed.set_footer(text=modal.footerText.value, icon_url=footerIcon or None)
        else:
            if footerIcon:
                embed.set_footer(text=ZWSP, icon_url=footerIcon)
            else:
                embed.remove_footer()

        if modal.colour.value:
            if modal.colour.value.lower() == "random":
                embed.colour = Colour.random()
            else:
                embed.colour = Colour(int(modal.colour.value, base=16))
        else:
            embed.colour = None

        if lib.discordUtil.embedEmpty(embed):
            embed.description = ZWSP
        await interaction.edit_original_message(embed=embed)


    @BasedCog.staticComponentCallback(StaticComponents.User_Embed_Edit_Images)
    async def editEmbedImages(self, interaction: Interaction, userId: str, *_):
        if userId and interaction.user.id != int(userId):
            return

        message = await self.messageForInteraction(interaction, "editEmbedImages", StaticComponents.User_Embed_Edit_Images)
        if message is None: return
        embed = message.embeds[0]

        modal = EmbedImageParams(title="Embed parameters", currentEmbed=embed)
        await interaction.response.send_modal(modal)
        if await modal.wait(): return

        authorName = ("" if embed.author.name in (None, ZWSP) else embed.author.name) if embed.author is not None else ""
        if modal.authorIcon.value:
            embed.set_author(name=authorName or ZWSP, icon_url=modal.authorIcon)
        else:
            if authorName:
                embed.set_author(name=authorName, icon_url=None)
            else:
                embed.remove_author()

        embed.set_thumbnail(url=modal.thumb.value or None)
        embed.set_image(url=modal.img.value or None)

        footerText = ("" if embed.footer.text in (None, ZWSP) else embed.footer.text) if embed.footer is not None else ""
        if modal.footerIcon.value:
            embed.set_footer(text=footerText or ZWSP, icon_url=modal.footerIcon)
        else:
            if footerText:
                embed.set_footer(text=footerText, icon_url=None)
            else:
                embed.remove_footer()

        if lib.discordUtil.embedEmpty(embed):
            embed.description = ZWSP
        await interaction.edit_original_message(embed=embed)

#endregion
#region commands

    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="sleep",
                            description="Shut down the bot.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_sleep(self, interaction: Interaction):
        """developer command saving all data to JSON and then shutting down the bot
        """
        self.bot.shutDownState = client.ShutDownState.shutdown
        await interaction.response.send_message("shutting down.")
        await self.bot.shutdown()


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="save",
                            description="Save all databases to JSON.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_save(self, interaction: Interaction):
        """developer command saving all databases to JSON
        """
        await interaction.response.defer(ephemeral=True)
        try:
            self.bot.saveAllDBs()
        except Exception as e:
            print("SAVING ERROR", e.__class__.__name__)
            print(traceback.format_exc())
            await interaction.followup.send(f"Saving failed - {type(e).__name__}", ephemeral=True)
            return
        print(utcnow().strftime("%H:%M:%S: Data saved manually!"))
        await interaction.followup.send("saved!", ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="say",
                            description="Say something in this channel.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_say(self, interaction: Interaction, content: Optional[str] = None, add_embed: bool = False, string_form: Optional[str] = None):
        """developer command sending a message to the same channel as the command is called in
        """
        if string_form is not None:
            await interaction.response.defer(thinking=False)
            await textChannel(interaction).send(**lib.discordUtil.messageArgsFromStr(string_form))
            return

        if content is None and add_embed == False:
            await interaction.response.send_message("Cannot send a message without content or an embed!", ephemeral=True)
            return

        content = content or ""
        embed = None

        if add_embed:
            embed = Embed()

            modal = EmbedTextParams(title="Embed parameters")
            await interaction.response.send_modal(modal)
            if await modal.wait(): return

            if modal.titleTxt.value:
                embed.title = modal.titleTxt.value
            if modal.authorName.value:
                embed.set_author(name=modal.authorName.value, icon_url=None)
            if modal.desc.value:
                embed.description = modal.desc.value
            if modal.footerText.value:
                embed.set_footer(text=modal.footerText.value, icon_url=None)
            if modal.colour.value:
                if modal.colour.value.lower() == "random":
                    embed.colour = Colour.random()
                else:
                    embed.colour = Colour(int(modal.colour.value, base=16))
            else:
                embed.colour = None
        
        view = messageEditorView(interaction.user.id, embed=embed)

        if embed is not None:
            if lib.discordUtil.embedEmpty(embed):
                embed.description = ZWSP
            await interaction.followup.send(content=content, embed=embed, ephemeral=True, view=view)
        else:
            await interaction.followup.send(content=content, ephemeral=True, view=view)

#endregion

async def setup(bot: client.BasedClient):
    await bot.add_cog(DevMiscCog(bot), guilds=cfg.developmentGuilds) # type: ignore[reportGeneralTypeIssues]
