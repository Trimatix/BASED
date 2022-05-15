from typing import Type, Union
from discord import Interaction
from ..cfg import cfg
from . import accessLevel


async def _checkLevel(level: accessLevel._AccessLevelBase, interaction: Interaction) -> bool:
    return await level.userHasAccess(interaction) \
            if issubclass(level, accessLevel.AccessLevelAsync) \
            else level.userHasAccess(interaction)


async def inferUserPermissions(interaction: Interaction) -> Type[accessLevel._AccessLevelBase]:
    """Get the commands access level of the user that triggered an interaction.
    
    :return: message.author's access level
    :rtype: Type[accessLevel._AccessLevelBase]
    """
    for levelName in cfg.userAccessLevels[::-1]:
        level = accessLevel._accessLevels[levelName]
        if await _checkLevel(level, interaction):
            return level
    return accessLevel.defaultAccessLevel()


def accessLevelSufficient(current: accessLevel._AccessLevelBase, required: accessLevel._AccessLevelBase) -> bool:
    return current._intLevel() >= required._intLevel()


async def userHasAccess(interaction: Interaction, level: accessLevel._AccessLevelBase) -> bool:
    return accessLevelSufficient(await inferUserPermissions(interaction), level)


def requireAccess(level: Union[Type[accessLevel._AccessLevelBase], str]):
    if isinstance(level, str):
        level = accessLevel.accessLevelNamed(level)
    async def inner(interaction: Interaction):
        return await userHasAccess(interaction, level)

    return inner
