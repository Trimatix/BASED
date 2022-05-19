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
    """Decide whether an access level is at least as high in the heirarchy as another

    :param current: The 'owned' access level
    :type current: accessLevel._AccessLevelBase
    :param required: The access level acting as a comparison point
    :type required: accessLevel._AccessLevelBase
    :return: `True` if `current` is at least as high in the access level heirarchy as `required`, `False` otherwise
    :rtype: bool
    """
    return current._intLevel() >= required._intLevel()


async def userHasAccess(interaction: Interaction, level: accessLevel._AccessLevelBase) -> bool:
    return accessLevelSufficient(await inferUserPermissions(interaction), level)


def requireAccess(level: Union[Type[accessLevel._AccessLevelBase], str]):
    """A command check that requires at least an access level of `level` to use the command.

    :param level: The access level to required
    :type level: Union[Type[accessLevel._AccessLevelBase], str]
    :return: The command check callback
    :rtype: Callable[[Interaction], bool]
    """
    if isinstance(level, str):
        level = accessLevel.accessLevelNamed(level)
    async def inner(interaction: Interaction):
        return await userHasAccess(interaction, level)

    return inner
