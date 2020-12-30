from . import ReactionMenu
from discord import Message, Member, User, Colour
from typing import Union
from ..cfg import cfg


class InlineConfirmationMenu(ReactionMenu.SingleUserReactionMenu):
    def __init__(self, msg : Message, targetMember : Union[Member, User], timeoutSeconds : int,
                    titleTxt : str = "", desc : str = "", col : Colour = Colour.blue(), footerTxt : str = "", img : str = "",
                    thumb : str = "", icon : str = "", authorName : str = ""):
        
        super().__init__(msg, targetMember, timeoutSeconds, options={cfg.defaultAcceptEmoji: ReactionMenu.DummyReactionMenuOption("Yes", cfg.defaultAcceptEmoji),
                                                                        cfg.defaultRejectEmoji: ReactionMenu.DummyReactionMenuOption("No", cfg.defaultRejectEmoji)},
                            returnTriggers=[cfg.defaultAcceptEmoji, cfg.defaultRejectEmoji], titleTxt=titleTxt, desc=desc, col=col, footerTxt=footerTxt,
                            img=img, thumb=thumb, icon=icon, authorName=authorName)
