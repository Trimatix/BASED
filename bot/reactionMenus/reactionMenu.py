from datetime import datetime
import inspect
from discord import Embed,  NotFound, HTTPException, Forbidden, TextChannel
from discord import Member, User
from .. import lib
from abc import abstractmethod, ABC, ABCMeta
from typing import Any, Awaitable, Generic, Optional, Protocol, Type, TypeVar, Union, Dict, List, cast
from ..client import BasedClient

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.orm.decl_api import DeclarativeAttributeIntercept

databaseMenuTypeNames: Dict[Type["DatabaseReactionMenu"], str] = {}
databaseNameMenuTypes: Dict[str, Type["DatabaseReactionMenu"]] = {}

class InMemoryReactionMenuOptionCallbackSync(Protocol):
    def __call__(self, user: Union[Member, User]) -> Any: ...


class InMemoryReactionMenuOptionCallbackAsync(Protocol):
    def __call__(self, user: Union[Member, User]) -> Awaitable[Any]: ...


MenuOptionCallbackType = Union[InMemoryReactionMenuOptionCallbackSync, InMemoryReactionMenuOptionCallbackAsync]

class AbcDeclarativeAttributeIntercept(DeclarativeAttributeIntercept, ABCMeta):
    """Intersectin of the ABC and DeclarativeBase meta classes.
    As of writing, ABCMeta only adds __new__, which DeclarativeAttributeIntercept does not add, so this should be fine.
    """
    ...


class DatabaseReactionMenuMeta(AbcDeclarativeAttributeIntercept):
    def __new__(mcls, name, bases, namespace, /, **kwargs):
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)

        if not issubclass(cls, DatabaseReactionMenu):
            return cls

        if cls in databaseMenuTypeNames:
            raise ValueError(f"{DatabaseReactionMenu.__name__} subclass names must be unique")

        if cls.__name__ in databaseNameMenuTypes:
            raise ValueError(f"{DatabaseReactionMenu.__name__} subclass names must be unique")
        
        databaseMenuTypeNames[cls] = cls.__name__
        databaseNameMenuTypes[cls.__name__] = cls

        return cls


class Base(DeclarativeBase): ...


class ReactionMenuOption(ABC):
    menuId: int
    emoji: lib.emojis.BasedEmoji
    name: Optional[str]
    value: Optional[str]
    onAdd: Optional[MenuOptionCallbackType]
    onRemove: Optional[MenuOptionCallbackType]

    async def add(self, user: Union[Member, User]):
        """Invoke this option's 'reaction added' functionality.
        This method is called by the owning reaction menu whenever a valid selection of this
        option is performed by a user.

        :param discord.Member member: The member adding the reaction
        :return: The result of the option's addFunc function, if one exists.
        """
        if self.onAdd is None: return

        result = self.onAdd(user)

        if inspect.iscoroutinefunction(self.onAdd):
            await result


    async def remove(self, user: Union[Member, User]):
        """Invoke this option's 'reaction removed' functionality.
        This method is called by the owning reaction menu whenever a valid de-selection of this
        option is performed by a user.

        :param discord.Member member: The member that removed the reaction
        :return: The result of the option's removeFunc function, if one exists.
        """
        if self.onRemove is None: return

        result = self.onRemove(user)

        if inspect.iscoroutinefunction(self.onRemove):
            await result


class InMemoryReactionMenuOption(ReactionMenuOption):
    """An option in a reaction menu. Reaction menu options must have a name and emoji.
    They may optionally have callbacks for when they are reacted/unreacted on their menu message.
    Callbacks accept a single positional argument, the user who performed the reaction.
    If a callback is a coroutine, it will be awaited.
    """

    def __init__(self, name: str, emoji: lib.emojis.BasedEmoji,
                    onAdd: Optional[MenuOptionCallbackType] = None,
                    onRemove: Optional[MenuOptionCallbackType] = None):
        """
        :param str name: The name of this option, as displayed in the menu embed.
        :param lib.emojis.BasedEmoji emoji: The emoji that a user must react with to trigger this option
        :param Optional[MenuOptionCallbackType] onAdd: The function to call when this option is added by a user
        :param Optional[MenuOptionCallbackType] onRemove: The function to call when this option is removed by a user
        """
        self.name = name
        self.emoji = emoji
        self.onAdd = onAdd
        self.onRemove = onRemove


    def __hash__(self) -> int:
        """Calculate a hash of this menu option from its repr string, based on the object's memory location.

        :return: A hash of this menu option
        :rtype: int
        """
        return hash(repr(self))
    

class DatabaseReactionMenuOption(ReactionMenuOption, Base, metaclass=AbcDeclarativeAttributeIntercept):
    id: Mapped[int] = mapped_column(primary_key=True)
    menuId: Mapped[int]
    emoji: Mapped[str]
    name: Mapped[Optional[str]]
    value: Mapped[Optional[str]]


TMenuOption = TypeVar("TMenuOption", bound=ReactionMenuOption)

class ReactionMenu(ABC, Generic[TMenuOption]):
    id: int
    channelId: int
    ownerId: Optional[int]
    private: Optional[bool]
    expiryTime: Optional[datetime]
    multipleChoice: Optional[bool]
    embed: Optional[Embed]
    options: List[TMenuOption]
    _timedOut: Optional[bool]

    @property
    def timedOut(self):
        if self._timedOut is None:
            raise ValueError("This menu is still active")
        
        return self._timedOut


    def _end(self, client: BasedClient, timedOut: bool):
        """Update the internal state to reflect that the menu is no longer active.
        This must be called by `end`.
        """
        self._timedOut = timedOut
        client.dispatch("based_reactionmenu_end", self)


    @abstractmethod
    async def end(self, client: BasedClient, timedOut: bool = False):
        """End execution of the menu. Do not override this method, instead use `onEnd`. 
        """
        ...


    async def onEnd(self, timedOut: bool):
        """Overrideable callback that is called when the menu ends.
        If `timedOut` is `True`, then the menu ended due to timeout.
        """
        pass


    def hasEmoji(self, emoji: lib.emojis.BasedEmoji) -> bool:
        return any(True for o in self.options if o.emoji == emoji)


    async def reactionAdded(self, emoji: lib.emojis.BasedEmoji, user: Union[Member, User]):
        """Invoke an option's behaviour when it is selected by a user.
        This method should be called during your discord client's on_reaction_add or on_raw_reaction_add event.

        :param lib.emojis.BasedEmoji emoji: The emoji that `user` reacted to the menu with
        :param Union[Member, User] user: The user that added the emoji reaction
        """
        if self.private and self.ownerId is not None and user.id != self.ownerId: return

        try:
            option = next(o for o in self.options if o.emoji == emoji)
        except StopIteration:
            raise KeyError(f"Unknown option: {emoji.sendable}")
        
        await option.add(user)


    async def reactionRemoved(self, emoji: lib.emojis.BasedEmoji, user: Union[Member, User]):
        """Invoke an option's behaviour when it is deselected by a user.
        This method should be called during your discord client's on_reaction_remove or on_raw_reaction_remove event.

        :param lib.emojis.BasedEmoji emoji: The emoji reaction that `user` removed from the menu
        :param Union[Member, User] user: The user that removed the emoji reaction
        """
        if self.private and self.ownerId is not None and user.id != self.ownerId: return

        try:
            option = next(o for o in self.options if o.emoji == emoji)
        except StopIteration:
            raise KeyError(f"Unknown option: {emoji.sendable}")
        
        await option.remove(user)


    def getMenuEmbed(self) -> Embed:
        """Generate the `Embed` representing the reaction menu, and that
        should be embedded into the menu's message.
        This will usually contain a short description of the menu, its options, and its expiry time.

        :return: An Embed representing the menu and its options
        :rtype: Embed 
        """
        embed = Embed() if self.embed is None else self.embed.copy()

        for option in self.options:
            embed.add_field(name=f"{option.emoji} : {option.name}", value=lib.discordUtil.ZWSP, inline=False)

        return embed


    async def updateMessage(self, client: BasedClient, refreshOptions=True):
        """Update the menu message by updating the embed.
        If `refreshOptions` is `True`, also remove all reactions and add new ones.
        """
        msg = client.get_partial_messageable(self.channelId).get_partial_message(self.id)
        await msg.edit(embed=self.getMenuEmbed())

        if refreshOptions:
            msg = await msg.fetch()

            try:
                await msg.clear_reactions()
            except Forbidden:
                for reaction in msg.reactions:
                    try:
                        # ignoring a warning here that Client.user can be None, if the client is not logged in.
                        # The client will always be logged in here, because menu changes can only be triggered by discord reactions.
                        await reaction.remove(client.user) # type: ignore[reportGeneralTypeIssues] 
                    except (HTTPException, NotFound):
                        pass

            for option in self.options:
                await msg.add_reaction(option.emoji.sendable)


    async def wait(self, client: BasedClient):
        """Wait for this reaction menu to end.

        :param client: The discord client to use for waiting.
        :type client: BasedClient
        """
        def check(menu: ReactionMenu):
            return menu.id == self.id
        
        await client.wait_for("based_reactionmenu_end", check=check)


class InMemoryReactionMenu(ReactionMenu[InMemoryReactionMenuOption]):
    def __init__(self, client: BasedClient, menuId: int, channelId: int,
                    options: List[InMemoryReactionMenuOption],
                    ownerId: Optional[int] = None, expiryTime: Optional[datetime] = None,
                    multipleChoice: Optional[bool] = None, embed: Optional[Embed] = None):
        self.id = menuId
        self.channelId = channelId
        self.options = options
        self.ownerId = ownerId
        self.expiryTime = expiryTime
        self.multipleChoice = multipleChoice
        self.embed = embed
        client.inMemoryReactionMenusDB[self.id] = self


    async def end(self, client: BasedClient, timedOut: bool = False):
        await self.onEnd(timedOut)
        client.inMemoryReactionMenusDB.pop(self.id, None)
        self._end(client, timedOut)

    
class DatabaseReactionMenu(ReactionMenu[DatabaseReactionMenuOption], Base, metaclass=DatabaseReactionMenuMeta):
    __tablename__ = "reactionMenu"

    id: Mapped[int] = mapped_column(primary_key=True)
    channelId: Mapped[int]
    menuType: Mapped[str]
    ownerId: Mapped[Optional[int]]
    expiryTime: Mapped[Optional[datetime]]
    multipleChoice: Mapped[Optional[bool]]
    options: Mapped[List[DatabaseReactionMenuOption]] = relationship()


    def __init__(self, **kw: Any):
        kw["menuType"] = type(self).__name__
        super().__init__(**kw)


    async def end(self, client: BasedClient, timedOut: bool = False):
        await self.onEnd(timedOut)

        async with client.sessionMaker() as session:
            for option in self.options:
                await session.delete(option)

            await session.delete(self)
            
        self._end(client, timedOut)


def isDatabaseMenuTypeName(clsName: str) -> bool:
    """Decide if `clsName` is the name of a `DatabaseReactionMenu` class.

    :param str clsName: The name of the class to look up
    :return: True if `clsName` corresponds to a `DatabaseReactionMenu` subclass, False otherwise
    :rtype: bool
    """
    return clsName in databaseNameMenuTypes


def databaseMenuClassFromName(clsName: str) -> Type[DatabaseReactionMenu]:
    """Retreive the existing `DatabaseReactionMenu` subclass that has the given class name.

    :param str clsName: The name of the class to retreive
    :return: A `DatabaseReactionMenu` subclass with the name `clsName`
    :rtype: Type[DatabaseReactionMenu]
    :raise KeyError: If no `DatabaseReactionMenu` subclass with the given name has been loaded
    """
    return databaseNameMenuTypes[clsName]
