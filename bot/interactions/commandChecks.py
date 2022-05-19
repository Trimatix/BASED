from typing import Type, Union
from discord import Interaction
from ..cfg import cfg
from . import accessLevels


async def _checkLevel(level: accessLevels._AccessLevelBase, interaction: Interaction) -> bool:
    return await level.userHasAccess(interaction) \
            if issubclass(level, accessLevels.AccessLevelAsync) \
            else level.userHasAccess(interaction)


async def inferUserPermissions(interaction: Interaction) -> Type[accessLevels._AccessLevelBase]:
    """Get the commands access level of the user that triggered an interaction.
    
    :return: message.author's access level
    :rtype: Type[accessLevels._AccessLevelBase]
    """
    for levelName in cfg.userAccessLevels[::-1]:
        level = accessLevels._accessLevels[levelName]
        if await _checkLevel(level, interaction):
            return level
    return accessLevels.defaultAccessLevel()


def accessLevelSufficient(current: accessLevels._AccessLevelBase, required: accessLevels._AccessLevelBase) -> bool:
    """Decide whether an access level is at least as high in the heirarchy as another

    :param current: The 'owned' access level
    :type current: accessLevels._AccessLevelBase
    :param required: The access level acting as a comparison point
    :type required: accessLevels._AccessLevelBase
    :return: `True` if `current` is at least as high in the access level heirarchy as `required`, `False` otherwise
    :rtype: bool
    """
    return current._intLevel() >= required._intLevel()


async def userHasAccess(interaction: Interaction, level: accessLevels._AccessLevelBase) -> bool:
    return accessLevelSufficient(await inferUserPermissions(interaction), level)


def requireAccess(level: Union[Type[accessLevels._AccessLevelBase], str]):
    """A command check that requires at least an access level of `level` to use the command.

    :param level: The access level to required
    :type level: Union[Type[accessLevels._AccessLevelBase], str]
    :return: The command check callback
    :rtype: Callable[[Interaction], bool]
    """
    if isinstance(level, str):
        level = accessLevels.accessLevelNamed(level)
    async def inner(interaction: Interaction):
        return await userHasAccess(interaction, level)

    return inner
