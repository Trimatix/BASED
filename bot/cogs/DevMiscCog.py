import traceback
from typing import Optional
from .. import client, lib
from ..lib.discordUtil import ZWSP, EMPTY_IMAGE
from discord import app_commands, Interaction, ButtonStyle, Embed, TextStyle, Colour, SelectOption
from discord.utils import utcnow, MISSING
from discord.ui import View, Modal, TextInput, Button, Select
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand, basedApp


class EmbedTextParams(Modal):
    titleTxt = TextInput(label="Title", required=False)
    authorName = TextInput(label="Author name", required=False)
    desc = TextInput(label="Description", required=False, style=TextStyle.paragraph)
    footerText = TextInput(label="Footer text", required=False)
    colour = TextInput(label="Colour (hex or RANDOM)", required=False)
    
    def __init__(self, *, title: str = MISSING, timeout: Optional[float] = None, custom_id: str = MISSING,
                    currentEmbed: Embed = None):
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
    authorIcon = TextInput(label="Author icon", required=False)
    thumb = TextInput(label="Thumbnail", required=False)
    img = TextInput(label="Image", required=False)
    footerIcon = TextInput(label="Footer icon", required=False)
    
    def __init__(self, *, title: str = MISSING, timeout: Optional[float] = None, custom_id: str = MISSING,
                    currentEmbed: Embed = None):
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
    fieldInline = TextInput(label="Inline? (y/n)", required=False, max_length=1, placeholder="n")
    
    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.defer(thinking=False)


async def sayConfirm(originalInteraction: Interaction, content: str, embed: Optional[Embed]):
    view = View()

    async def send(interaction: Interaction):
        await interaction.response.edit_message("sent!", view=None)
        if lib.discordUtil.embedEmpty(embed):
            embed.description = ZWSP
        await interaction.channel.send(content=content, embed=embed)
        view.stop()

    async def cancel(interaction: Interaction):
        await interaction.response.defer(thinking=False)
        await interaction.edit_original_message(view=None)
        view.stop()

    async def addField(interaction: Interaction):
        modal = EmbedFieldParams(title="Field Parameters")

        await interaction.response.send_modal(modal)
        if await modal.wait(): view.stop()
        
        embed.add_field(name=modal.fieldName.value or ZWSP, value=modal.fieldValue.value or ZWSP, inline=modal.fieldInline.value.lower() == "y")
        if lib.discordUtil.embedEmpty(embed):
            emptyEmbed = True
            embed.description = ZWSP
        else:
            emptyEmbed = False
        await interaction.edit_original_message(embed=embed)
        if emptyEmbed:
            embed.description = None

    async def removeField(interaction: Interaction):
        if not embed.fields:
            await interaction.response.send_message("The embed has no fields!", ephemeral=True)
            return

        async def stopSelectorView(interaction: Interaction):
            selectedFieldIndices = sorted([int(i) for i in fieldSelector.values], reverse=True)
            for i in selectedFieldIndices:
                embed.remove_field(i)

            if lib.discordUtil.embedEmpty(embed):
                emptyEmbed = True
                embed.description = ZWSP
            else:
                emptyEmbed = False
            view.remove_item(fieldSelector)
            await interaction.response.edit_message(embed=embed, view=view)
            if emptyEmbed:
                embed.description = None

        fieldSelector = Select(options=[SelectOption(label=f"{i + 1}. {field.name}", value=str(i)) for i, field in enumerate(embed.fields)], max_values=25)
        fieldSelector.callback = stopSelectorView
        view.add_item(fieldSelector)

        await interaction.response.edit_message(view=view)

    async def editEmbedText(interaction: Interaction):
        modal = EmbedTextParams(title="Embed Parameters", currentEmbed=embed)

        await interaction.response.send_modal(modal)
        if await modal.wait(): view.stop()
        
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
            emptyEmbed = True
            embed.description = ZWSP
        else:
            emptyEmbed = False
        await interaction.edit_original_message(embed=embed)
        if emptyEmbed:
            embed.description = None

    async def editEmbedImages(interaction: Interaction):
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
            emptyEmbed = True
            embed.description = ZWSP
        else:
            emptyEmbed = False
        await interaction.edit_original_message(embed=embed)
        if emptyEmbed:
            embed.description = None

    confirmButton = Button(style=ButtonStyle.green, label="send")
    confirmButton.callback = send
    cancelButton = Button(style=ButtonStyle.red, label="cancel")
    cancelButton.callback = cancel
    view.add_item(cancelButton).add_item(confirmButton)
    if embed is not None:
        addFieldButton = Button(style=ButtonStyle.blurple, label="add embed field")
        addFieldButton.callback = addField
        view.add_item(addFieldButton)

        removeFieldButton = Button(style=ButtonStyle.blurple, label="remove embed field")
        removeFieldButton.callback = removeField
        view.add_item(removeFieldButton)

        editEmbedTextButton = Button(style=ButtonStyle.blurple, label="edit embed text")
        editEmbedTextButton.callback = editEmbedText
        view.add_item(editEmbedTextButton)

        editEmbedImagesButton = Button(style=ButtonStyle.blurple, label="edit embed images")
        editEmbedImagesButton.callback = editEmbedImages
        view.add_item(editEmbedImagesButton)

    if lib.discordUtil.embedEmpty(embed):
        emptyEmbed = True
        embed.description = ZWSP
    else:
        emptyEmbed = False
    await originalInteraction.followup.send(content=content, embed=embed, ephemeral=True, view=view)
    if emptyEmbed:
        embed.description = None


class DevMiscCog(basedApp.BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="sleep",
                            description="Shut down the bot.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_sleep(self, interaction: Interaction):
        """developer command saving all data to JSON and then shutting down the bot
        """
        self.bot.shutDownState = client.ShutDownState.shutdown
        await interaction.response.send("shutting down.")
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
    async def dev_cmd_say(self, interaction: Interaction, content: str = None, add_embed: bool = False, string_form: str = None):
        """developer command sending a message to the same channel as the command is called in
        """
        if string_form is not None:
            await interaction.response.defer(thinking=False)
            await interaction.channel.send(**lib.discordUtil.messageArgsFromStr(string_form))
            return

        if content is None and add_embed == False:
            await interaction.response.send_message("Cannot send a message without content or an embed!", ephemeral=True)

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

        await sayConfirm(interaction, content, embed)


async def setup(bot: client.BasedClient):
    await bot.add_cog(DevMiscCog(bot), guilds=cfg.developmentGuilds)
