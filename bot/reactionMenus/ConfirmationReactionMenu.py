from . import ReactionMenu
from discord import Message, Member, User, Colour
from typing import Union
from ..cfg import cfg


class InlineConfirmationMenu(ReactionMenu.InlineReactionMenu):
    def __init__(self, msg : Message, targetMember : Union[Member, User], timeoutSeconds : int,
                    titleTxt : str = "", desc : str = "", col : Colour = Colour.blue(), footerTxt : str = "", img : str = "",
                    thumb : str = "", icon : str = "", authorName : str = ""):
        
        super().__init__(msg, targetMember, timeoutSeconds, options={cfg.defaultEmojis.accept: ReactionMenu.DummyReactionMenuOption("Yes", cfg.defaultEmojis.accept),
                                                                        cfg.defaultEmojis.reject: ReactionMenu.DummyReactionMenuOption("No", cfg.defaultEmojis.reject)},
                            returnTriggers=[cfg.defaultEmojis.accept, cfg.defaultEmojis.reject], titleTxt=titleTxt, desc=desc, col=col, footerTxt=footerTxt,
                            img=img, thumb=thumb, icon=icon, authorName=authorName)
