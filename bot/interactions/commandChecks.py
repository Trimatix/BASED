from typing import Union
from discord import app_commands, Interaction, Message, User, Member
from ..cfg import cfg

_levels = {l: cfg.userAccessLevels.index(l) for l in cfg.userAccessLevels}

def inferUserPermissions(interaction: Interaction) -> str:
    """Get the commands access level of the user that sent the given message.
    
    :return: message.author's access level, as an index of cfg.userAccessLevels
    :rtype: int
    """
    if interaction.user.id in cfg.developers:
        return cfg.basicAccessLevels.developer
    elif isinstance(interaction.user, Member) and interaction.channel.permissions_for(interaction.user).administrator:
        return cfg.basicAccessLevels.serverAdmin
    else:
        return cfg.basicAccessLevels.user


def requireAccess(level: str):
    def inner(interaction: Interaction):
        return _levels[inferUserPermissions(interaction)] >= _levels[level]

    return inner
