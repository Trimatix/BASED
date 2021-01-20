from . import reactionMenu
from discord import Message, Member, User, Colour
from typing import Union
from ..cfg import cfg


class InlineConfirmationMenu(reactionMenu.InlineReactionMenu):
    def __init__(self, msg: Message, targetMember: Union[Member, User], timeoutSeconds: int,
                 titleTxt: str = "", desc: str = "", col: Colour = Colour.blue(), footerTxt: str = "", img: str = "",
                 thumb: str = "", icon: str = "", authorName: str = ""):

        options = {cfg.defaultEmojis.accept: reactionMenu.DummyReactionMenuOption("Yes", cfg.defaultEmojis.accept),
                    cfg.defaultEmojis.reject: reactionMenu.DummyReactionMenuOption("No", cfg.defaultEmojis.reject)}

        super().__init__(msg, targetMember, timeoutSeconds, options=options, img=img, thumb=thumb, icon=icon,
                            authorName=authorName, returnTriggers=[cfg.defaultEmojis.accept, cfg.defaultEmojis.reject],
                            titleTxt=titleTxt, desc=desc, col=col, footerTxt=footerTxt)
