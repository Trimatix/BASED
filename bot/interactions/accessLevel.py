from typing import Type
from ..cfg import cfg
from abc import ABC, abstractmethod
from discord import Interaction, Member


class _flag:
    pass


_MISSING = _flag()


class _AccessLevelBase(ABC):
    name: str = _MISSING
    
    @classmethod
    def _intLevel(cls):
        return cfg.userAccessLevels.index(cls.name)


class _ImportPlaceholder(_AccessLevelBase):
    pass


_accessLevels: dict[str, _AccessLevelBase] = {}
_defaultAccessLevel: Type[_AccessLevelBase] = _ImportPlaceholder


def accessLevelNamed(name: str) -> Type[_AccessLevelBase]:
    return _accessLevels[name]


def accessLevelWithIntLevel(level: int) -> Type[_AccessLevelBase]:
    if level < 0 or level >= len(cfg.userAccessLevels):
        raise ValueError(f"Invalid access level int level: {level}. Must be between 0 and {len(cfg.userAccessLevels) - 1}")
    return accessLevelNamed(cfg.userAccessLevels[level])


def defaultAccessLevel() -> Type[_AccessLevelBase]:
    return _defaultAccessLevel


def accessLevel(name: str = None, default: bool = False):
    """Register an Access Level class for use by a `BasedClient`.

    :param accessLevel: The class to register
    :type accessLevel: Type[_AccessLevelBase]
    :param name: The name of the access level, from `cfg` (Default `accessLevel.name`)
    :type name: Optional[str], optional
    :raises ValueError: When `accessLevel` is not an access level subclass
    :param default: Whether to use this access level as the default, lowest-level of access (Default False)
    :type default: bool
    """
    def inner(accessLevel: Type[_AccessLevelBase], name = name, default = default):
        global _defaultAccessLevel
        if not issubclass(accessLevel, _AccessLevelBase):
            raise ValueError(f"decorator is only valid for use on access level subclasses")
        if not isinstance(name, str):
            name = accessLevel.name
        elif not isinstance(accessLevel.name, str):
            accessLevel.name = name
        if not isinstance(name, str):
            raise ValueError(f"{accessLevel} does not have a name, or invalid name provided. Give a `str` either in your `accessLevel` decorator, in the `{accessLevel.__name__}.name` class attribute")
        if name in _accessLevels:
            raise KeyError(f"An access level is already registered with name {name}")
        _accessLevels[name] = accessLevel
        if default:
            _defaultAccessLevel = accessLevel
        return accessLevel
    return inner


class AccessLevel(_AccessLevelBase):
    @classmethod
    @abstractmethod
    def userHasAccess(cls, interaction: Interaction) -> bool:
        raise NotImplementedError()


class AccessLevelAsync(_AccessLevelBase):
    @classmethod
    @abstractmethod
    async def userHasAccess(cls, interaction: Interaction) -> bool:
        raise NotImplementedError()


@accessLevel(cfg.basicAccessLevels.developer)
class DeveloperAccessLevel(AccessLevel):
    @classmethod
    def userHasAccess(cls, interaction: Interaction) -> bool:
        return interaction.user.id in cfg.developers


@accessLevel(cfg.basicAccessLevels.serverAdmin)
class ServerAdministratorAccessLevel(AccessLevel):
    @classmethod
    def userHasAccess(cls, interaction: Interaction) -> bool:
        return isinstance(interaction.user, Member) and interaction.channel.permissions_for(interaction.user).administrator


@accessLevel(cfg.basicAccessLevels.user, default=True)
class UserAccessLevel(AccessLevel):
    @classmethod
    def userHasAccess(cls, interaction: Interaction) -> bool:
        return True


@accessLevel("mod")
class ModeratorAccessLevel(AccessLevel):
    @classmethod
    def userHasAccess(cls, interaction: Interaction) -> bool:
        return ServerAdministratorAccessLevel.userHasAccess(interaction)
        