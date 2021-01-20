# TODO: Write a targettable ReactionMenuOption subclass, that implements targetMember and targetRole on a per-option basis.
# Use this to write ReactionRolePickers with multipleChoice=False!

from ..scheduling.timedTask import TimedTask
import inspect
from discord import Embed, Colour, NotFound, HTTPException, Forbidden, Member, User, Message, Role, RawReactionActionEvent
from ..cfg import cfg
from .. import botState, lib
from abc import abstractmethod
from typing import Union, Dict, List
import asyncio
from types import FunctionType
from ..baseClasses import serializable
from . import expiryFunctions


class ReactionMenuOption(serializable.Serializable):
    """An abstract class representing an option in a reaction menu.
    Reaction menu options must have a name and emoji. They may optionally have a function to call when added,
    a function to call when removed, and arguments for each.
    If either function has a keyword argument called 'reactingUser', the user who added/removed the reaction will
    be passed there. TODO: Should probably change this to reactingMember

    :var name: The name of this option, as displayed in the menu embed.
    :vartype name: str
    :var emoji: The emoji that a user must react with to trigger this option
    :vartype emoji: lib.emojis.BasedEmoji
    :var addFunc: The function to call when this option is added by a user
    :vartype addFunc: FunctionType
    :var removeFunc: The function to call when this option is removed by a user
    :vartype removeFunc: FunctionType
    :var addArgs: The arguments to pass to addFunc. No type checking is done on this parameter,
                    but a dict is recommended as a close replacement for keyword args.
    :var removeArgs: The arguments to pass to removeFunc.
    :var addIsCoroutine: Whether or not addFuc is a coroutine and must be awaited
    :vartype addIsCoroutine: bool
    :var addIncludeUser: Whether or not to give the reacting user as a keyword argument to addFunc
    :vartype addIncludeUser: bool
    :var addHasArgs: Whether addFunc takes arguments, and addArgs should be attempt to be passed
    :vartype addHasArgs: bool
    :var removeIsCoroutine: Whether or not removeFuc is a coroutine and must be awaited
    :vartype removeIsCoroutine: bool
    :var removeIncludeUser: Whether or not to give the reacting user as a keyword argument to removeFunc
    :vartype removeIncludeUser: bool
    :var removeHasArgs: Whether removeFunc takes arguments, and removeArgs should be attempt to be passed
    :vartype removeHasArgs: bool
    """

    def __init__(self, name: str, emoji: lib.emojis.BasedEmoji, addFunc: FunctionType = None, addArgs=None,
                    removeFunc: FunctionType = None, removeArgs=None):
        """
        :param str name: The name of this option, as displayed in the menu embed.
        :param lib.emojis.BasedEmoji emoji: The emoji that a user must react with to trigger this option
        :param function addFunc: The function to call when this option is added by a user
        :param function removeFunc: The function to call when this option is removed by a user
        :param addArgs: The arguments to pass to addFunc. No type checking is done on this parameter,
                        but a dict is recommended as a close replacement for keyword args.
        :param removeArgs: The arguments to pass to removeFunc.
        """

        self.name = name
        self.emoji = emoji

        self.addFunc = addFunc
        self.addArgs = addArgs
        self.addIsCoroutine = addFunc is not None and inspect.iscoroutinefunction(addFunc)
        self.addIncludeUser = addFunc is not None and 'reactingUser' in inspect.signature(addFunc).parameters
        self.addHasArgs = addFunc is not None and len(inspect.signature(
            addFunc).parameters) != (1 if self.addIncludeUser else 0)

        self.removeFunc = removeFunc
        self.removeArgs = removeArgs
        self.removeIsCoroutine = removeFunc is not None and inspect.iscoroutinefunction(removeFunc)
        self.removeIncludeUser = removeFunc is not None and 'reactingUser' in inspect.signature(addFunc).parameters
        self.removeHasArgs = removeFunc is not None and len(inspect.signature(
            removeFunc).parameters) != (1 if self.removeIncludeUser else 0)


    async def add(self, member: Union[Member, User]):
        """Invoke this option's 'reaction added' functionality.
        This method is called by the owning reaction menu whenever this option is added by any user
        that matches the menu's restrictions, if any apply (e.g targetMember, targetRole)

        :param discord.Member member: The member adding the reaction
        :return: The result of the option's addFunc function, if one exists.
        """
        if self.addFunc is not None:
            if self.addIncludeUser:
                if self.addHasArgs:
                    return await self.addFunc(self.addArgs, reactingUser=member) if self.addIsCoroutine else \
                                self.addFunc(self.addArgs, reactingUser=member)
                return await self.addFunc(reactingUser=member) if self.addIsCoroutine else \
                                self.addFunc(reactingUser=member)
            if self.addHasArgs:
                return await self.addFunc(self.addArgs) if self.addIsCoroutine else self.addFunc(self.addArgs)
            return await self.addFunc() if self.addIsCoroutine else self.addFunc()


    async def remove(self, member: Union[Member, User]):
        """Invoke this option's 'reaction removed' functionality.
        This method is called by the owning reaction menu whenever this option is removed by any user
        that matches the menu's restrictions, if any apply (e.g targetMember, targetRole)

        :param discord.Member member: The member that removed the reaction
        :return: The result of the option's removeFunc function, if one exists.
        """
        if self.removeFunc is not None:
            if self.removeIncludeUser:
                if self.removeHasArgs:
                    return await self.removeFunc(self.removeArgs, reactingUser=member) if self.removeIsCoroutine else \
                                self.removeFunc(self.removeArgs, reactingUser=member)
                return await self.removeFunc(reactingUser=member) if self.removeIsCoroutine else \
                                self.removeFunc(reactingUser=member)
            if self.removeHasArgs:
                return await self.removeFunc(self.removeArgs) if self.removeIsCoroutine else self.removeFunc(self.removeArgs)
            return await self.removeFunc() if self.removeIsCoroutine else self.removeFunc()


    def __hash__(self) -> int:
        """Calculate a hash of this menu option from its repr string.
        As of writing, this is based on the object's memory location.

        :return: A hash of this menu option
        :rtype: int
        """
        return hash(repr(self))


    @abstractmethod
    def toDict(self, **kwargs) -> dict:
        """Serialize this menu option into dictionary format for saving to file.
        This is a base, abstract definition that does not encode option functionality (i.e function calls and arguments).

        A generic but rather messy implementation for saving an option's addFunc and removeFunc could be written as follows:
        Saving:
        - Get the name of the module where the function reference is located using func.__module__
        - Get the name of the function reference using func.__name__
        Where func is addFunc or removeFunc as needed.

        Loading:
        Find the function reference from the module_name and function_name with one of:
        - getattr(globals()[module_name], function_name)
        - getattr(sys.modules[module_name], function_name)

        This is obviously a less than ideal implementation, and there are likely to be other solutions.

        TODO: Add type, similar to reaction menu todict, to allow dummy options to be recreated from dict
        :return: A dictionary containing rudimentary information about the menu option,
                to be used in conjunction with other type-specific information when reconstructing this menu option.
        :rtype: dict
        """
        return {"name": self.name, "emoji": self.emoji.toDict(**kwargs)}


    @classmethod
    def fromDict(cls, data: dict, **kwargs):
        raise NotImplementedError("Attempted to fromDict an unserializable menu option type: " + cls.__name__)


class NonSaveableReactionMenuOption(ReactionMenuOption):
    """A basic concrete class for instancing ReactionMenuOptions without the possibility of saving them to file.
    When creating a ReactionMenuOption subclass that can be saved to file, do not inherit from this class.
    Instead, inherit directly from ReactionMenuOption or another suitable subclass that is not marked as unsaveable.
    """

    def __init__(self, name: str, emoji: lib.emojis.BasedEmoji, addFunc: FunctionType = None, addArgs=None,
                        removeFunc: FunctionType = None, removeArgs=None):
        """
        :param str name: The name of this option, as displayed in the menu embed.
        :param lib.emojis.BasedEmoji emoji: The emoji that a user must react with to trigger this option
        :param function addFunc: The function to call when this option is added by a user
        :param function removeFunc: The function to call when this option is removed by a user
        :param addArgs: The arguments to pass to addFunc. No type checking is done on this parameter,
                        but a dict is recommended as a close replacement for keyword args.
        :param removeArgs: The arguments to pass to removeFunc.
        """
        super(NonSaveableReactionMenuOption, self).__init__(name, emoji, addFunc=addFunc, addArgs=addArgs,
                                                            removeFunc=removeFunc, removeArgs=removeArgs)


    def toDict(self, **kwargs) -> dict:
        """Unimplemented.
        This class should only be used for reaction menu options that will not be saved to file.

        :raise NotImplementedError: Always.
        """
        raise NotImplementedError("Attempted to call toDict on a non-saveable reaction menu option")


class DummyReactionMenuOption(ReactionMenuOption):
    """A reaction menu option with no function calls.
    A prime example is ReactionPollMenu, where adding and removing options need not have any functionality.
    """

    def __init__(self, name: str, emoji: lib.emojis.BasedEmoji):
        """
        :param str name: The name of this option, as displayed in the menu embed.
        :param lib.emojis.BasedEmoji emoji: The emoji that a user must react with to trigger this option
        """
        super(DummyReactionMenuOption, self).__init__(name, emoji)


    def toDict(self, **kwargs) -> dict:
        """Serialize this menu option into dictionary format for saving to file.
        Since dummy reaction menu options have no on-toggle functionality, the resulting base dictionary contains
        all information needed to reconstruct this option instance.

        :return: A dictionary containing all necessary information to reconstruct this option instance
        :rtype: dict
        """
        return super(DummyReactionMenuOption, self).toDict(**kwargs)


class ReactionMenu(serializable.Serializable):
    """A versatile class implementing emoji reaction menus.
    This class can be used as-is, to create unsaveable reaction menus of any type, with vast possibilities for behaviour.
    ReactionMenu need only be extended in the following cases:
    - When creating a 'preset' class with a new constructor creating a commonly used menu format, such as ReactionRolePicker
    - Your reaction menu should be saveable to file to be reloaded after a bot restart, such as ReactionPollMenu
    - The default getMenuEmbed method is inadequate
    - You require specialized behaviour handled/triggered outside of reactions.
      For example, a menu whose content may be changed via commands.

    How to use this class:
    1. Send a message
    2. (optional) Create a TimedTask that will call a menu deleting function (e.g deleteReactionMenu)
                  and pass your new message ID on expiry
                  TODO: add a constructor flag and TimedTask config data class to ReactionMenu constructor for
                        autoscheduling menu expiry on menu creation
    3. Pass your new message and TimedTask to the ReactionMenu constructor, also specifying a dictionary of menu options
    4. Call updateMessage on your new ReactionMenu instance
    5. Use discord's client events of either on_reaction_add and on_reaction_remove or on_raw_reaction_add and
       on_raw_reaction_remove to call your new menu's reactionAdded and reactionRemoved methods
       (bot.py has this behaviour already)
       TODO: Make reactionAdded and reactionRemoved ignore emoji that are not options in the menu

    The real power of this class can be harnessed by binding function calls to individual menu option reactions when
    creating your options dictionary. A great example of this is in ReactionRolePicker, which actually has no extra
    behaviour added over ReactionMenu. It acts more as a ReactionMenu preset, defining a new constructor which transforms
    a dictionary of emojis to roles into an options dictionary, where each option's addFunc is bound to a role granting
    function, and its removeFunc is bound to a role removing function. The only extra behaviour ReactionRolePickerOption
    implements over ReactionMenuOption is the addition of its associated role ID being saved during toDict.
    
    The options in your options dictionary do not have to be of the same type - each option could have completely
    different behaviour. The only consideration you may need to make when creating such an object is whether or
    not you wish for it to be saveable - in which case, you should extend ReactionMenu into a new module,
    providing a custom toDict method and fromDict function.

    :var msg: the message where this menu is embedded
    :vartype msg: discord.Message
    :var options: A dictionary storing all of the menu's options and their behaviour
    :vartype options: dict[lib.emojis.BasedEmoji, ReactionMenuOption]
    :var titleTxt: The content of the embed title
    :vartype titleTxt: str
    :var desc: he content of the embed description; appears at the top below the title
    :vartype desc: str
    :var col: The colour of the embed's side strip
    :vartype col: discord.Colour
    :var footerTxt: Secondary description appearing in darker font at the bottom of the embed
    :vartype footerTxt: str
    :var img: URL to a large icon appearing as the content of the embed, left aligned like a field
    :vartype img: str
    :var thumb: URL to a larger image appearing to the right of the title
    :vartype thumb: str
    :var icon: URL to a smaller image to the left of authorName. AuthorName is required for this to be displayed.
    :vartype icon: str
    :var authorName: Secondary, smaller title for the embed
    :vartype authorName: str
    :var timeout: The TimedTask responsible for expiring this menu
    :vartype timeout: TimedTask
    :var targetMember: The only discord.Member that is able to interact with this menu. All other reactions are ignored
    :vartype targetMember: discord.Member
    :var targetRole: In order to interact with this menu, users must possess this role. All other reactions are ignored
    :vartype targetRole: discord.Role
    :var saveable: Class attribute indicating whether or not this type of ReactionMenu can be saved to file.
                    If not, this menu will be forcibly deleted before bot shutdown.
    :vartype saveable: bool
    """
    saveable = False

    def __init__(self, msg: Message, options: Dict[lib.emojis.BasedEmoji, ReactionMenuOption] = None,
                 titleTxt: str = "", desc: str = "", col: Colour = Colour.blue(), timeout: TimedTask = None,
                 footerTxt: str = "", img: str = "", thumb: str = "", icon: str = "",
                 authorName: str = "", targetMember: Member = None, targetRole: Role = None):
        """
        :param discord.Message msg: the message where this menu is embedded
        :param options: A dictionary storing all of the menu's options and their behaviour (Default {})
        :type options: dict[lib.emojis.BasedEmoji, ReactionMenuOption]
        :param str titleTxt: The content of the embed title (Default "")
        :param str desc: he content of the embed description; appears at the top below the title (Default "")
        :param discord.Colour col: The colour of the embed's side strip (Default None)
        :param str footerTxt: Secondary description appearing in darker font at the bottom of the embed
                                (Default time until menu expiry if timeout is not None, "" otherwise)
        :param str img: URL to a large icon appearing as the content of the embed, left aligned like a field (Default "")
        :param str thumb: URL to a larger image appearing to the right of the title (Default "")
        :param str icon: URL to a smaller image to the left of authorName.
                        AuthorName is required for this to be displayed. (Default "")
        :param str authorName: Secondary, smaller title for the embed (Default "")
        :param TimedTask timeout: The TimedTask responsible for expiring this menu (Default None)
        :param discord.Member targetMember: The only discord.Member that is able to interact with this menu.
                                            All other reactions are ignored (Default None)
        :param discord.Role targetRole: In order to interact with this menu, users must possess this role.
                                        All other reactions are ignored (Default None)
        """

        if footerTxt == "" and timeout is not None:
            footerTxt = "This menu will expire in " + lib.timeUtil.td_format_noYM(timeout.expiryDelta) + "."

        # discord.message
        self.msg = msg
        # Dict of lib.emojis.BasedEmoji: ReactionMenuOption
        self.options = options if options is not None else {}

        self.titleTxt = titleTxt
        self.desc = desc
        self.col = col if col is not None else Colour.blue()
        self.footerTxt = footerTxt
        self.img = img
        self.thumb = thumb
        self.icon = icon
        self.authorName = authorName
        self.timeout = timeout
        self.targetMember = targetMember
        self.targetRole = targetRole


    def hasEmojiRegistered(self, emoji: lib.emojis.BasedEmoji) -> bool:
        """Decide whether or not the given emoji is an option in this menu

        :param lib.emojis.BasedEmoji emoji: The emoji to test for membership
        :return: True if emoji is an option in this menu, False otherwise.
        :rtype: bool
        """
        return emoji in self.options


    async def reactionAdded(self, emoji: lib.emojis.BasedEmoji, member: Union[Member, User]):
        """Invoke an option's behaviour when it is selected by a user.
        This method should be called during your discord client's on_reaction_add or on_raw_reaction_add event.

        If a targetMember was specified in this reaction menu's constructor, option behaviour will only be triggered
        if member is targetMember.
        If a targetRole was specified in this reaction menu's constructor, option behaviour will only be triggered
        if member has targetRole.
        Both may be specified and required.

        :param lib.emojis.BasedEmoji emoji: The emoji that member reacted to the menu with
        :param discord.Member member: The member that added the emoji reaction
        :return: The result of the corresponding menu option's addFunc, if any
        """
        if (self.targetMember is not None and \
                member != self.targetMember):
            return

        if self.targetRole is not None and \
                self.targetRole not in member.roles:
            return

        return await self.options[emoji].add(member)


    async def reactionRemoved(self, emoji: lib.emojis.BasedEmoji, member: Union[Member, User]):
        """Invoke an option's behaviour when it is deselected by a user.
        This method should be called during your discord client's on_reaction_remove or on_raw_reaction_remove event.

        If a targetMember was specified in this reaction menu's constructor, option behaviour will only be triggered
        if member is targetMember.
        If a targetRole was specified in this reaction menu's constructor, option behaviour will only be triggered
        if member has targetRole.
        Both may be specified and required.

        :param lib.emojis.BasedEmoji emoji: The emoji reaction that member removed from the menu
        :param discord.Member member: The member that removed the emoji reaction
        :return: The result of the corresponding menu option's removeFunc, if any
        """
        if self.targetMember is not None and \
                member != self.targetMember:
            return

        if self.targetRole is not None and \
                self.targetRole not in member.roles:
            return

        return await self.options[emoji].remove(member)


    def getMenuEmbed(self) -> Embed:
        """Generate the discord.Embed representing the reaction menu, and that
        should be embedded into the menu's message.
        This will usually contain a short description of the menu, its options, and its expiry time.

        :return: A discord.Embed representing the menu and its options
        :rtype: discord.Embed 
        """
        menuEmbed = Embed(title=self.titleTxt, description=self.desc, colour=self.col)
        if self.footerTxt != "":
            menuEmbed.set_footer(text=self.footerTxt)
        menuEmbed.set_image(url=self.img)
        if self.thumb != "":
            menuEmbed.set_thumbnail(url=self.thumb)
        if self.icon != "":
            menuEmbed.set_author(name=self.authorName, icon_url=self.icon)

        for option in self.options:
            menuEmbed.add_field(name=option.sendable + " : " + self.options[option].name, value="‎", inline=False)

        return menuEmbed


    async def updateMessage(self, noRefreshOptions=False):
        """Update the menu message by removing all reactions, replacing any existing embed with
        up to date embed content, and readd all of the menu's option reactions.
        """
        await self.msg.edit(embed=self.getMenuEmbed())

        if not noRefreshOptions:
            self.msg = await self.msg.channel.fetch_message(self.msg.id)

            try:
                await self.msg.clear_reactions()
            except Forbidden:
                for reaction in self.msg.reactions:
                    try:
                        await reaction.remove(botState.client.user)
                    except (HTTPException, NotFound):
                        pass

            for option in self.options:
                await self.msg.add_reaction(option.sendable)


    async def delete(self):
        """⚠ WARNING: DO NOT SET THIS AS YOUR MENU'S TIMEDTASK EXPIRY FUNCTION. This method calls the menu's
        TimedTask expiry function.
        
        Forcibly delete the menu.
        If a timeout TimedTask was defined in this menu's constructor, this will be forcibly expired.
        If no TimedTask was given, the menu will default to calling deleteReactionMenu.
        """
        if self.timeout is None:
            await expiryFunctions.deleteReactionMenu(self.msg.id)
        else:
            await self.timeout.forceExpire()


    def toDict(self, **kwargs) -> dict:
        """Serialize this ReactionMenu into dictionary format for saving to file.
        This is a base, concrete implementation that saves all information required to recreate a ReactionMenu instance;
        when extending ReactionMenu, you will likely wish to overload this method, using super.toDict as a base for your
        implementation. For an example, see ReactionPollMenu.toDict

        This method relies on your chosen ReactionMenuOption objects having a concrete, SAVEABLE toDict method.
        If any option in the menu is unsaveable, the menu becomes unsaveable.
        """
        optionsDict = {}
        for reaction in self.options:
            optionsDict[reaction.sendable] = self.options[reaction].toDict(**kwargs)

        data = {"channel": self.msg.channel.id, "msg": self.msg.id, "options": optionsDict,
                "type": self.__class__.__name__, "guild": self.msg.channel.guild.id}

        if self.titleTxt != "":
            data["titleTxt"] = self.titleTxt

        if self.desc != "":
            data["desc"] = self.desc

        if self.col != Colour.blue():
            data["col"] = self.col.to_rgb()

        if self.footerTxt != "":
            data["footerTxt"] = self.footerTxt

        if self.img != "":
            data["img"] = self.img

        if self.thumb != "":
            data["thumb"] = self.thumb

        if self.icon != "":
            data["icon"] = self.icon

        if self.authorName != "":
            data["authorName"] = self.authorName

        if self.timeout != None:
            data["timeout"] = self.timeout.expiryTime.timestamp()

        if self.targetMember is not None:
            data["targetMember"] = self.targetMember.id

        if self.targetRole is not None:
            data["targetRole"] = self.targetRole.id

        return data


    @classmethod
    def fromDict(cls, data: dict, **kwargs):
        raise NotImplementedError("Attempted to fromDict an unserializable menu type: " + cls.__name__)


class CancellableReactionMenu(ReactionMenu):
    """A simple ReactionMenu extension that adds an extra 'cancel' option to your given options dictionary.
    The 'cancel' option will call the menu's delete method. No extra restrictions beyond targetMember/targetRole are placed
    on members who may cancel the menu. 

    If CancellableReactionMenu is extended into a saveable menu class, the cancel option will not be included in the menu's
    dictionary-serialized representation. This is fine, since the constructor in your saveable subclass
    of CancellableReactionMenu must call super.__init__, which will add the cancel option back in again.
    TODO: Currently, if a different cancelEmoji is specified, it will not be saved to file, and it must be specified again
            when reloading the menu. Just save the cancel emoji in the dict, outside of options

    :var cancelEmoji: The emoji used for the menu's cancel button.
    :vartype cancelEmoji: lib.emojis.BasedEmoji
    """

    def __init__(self, msg: Message, options: Dict[lib.emojis.BasedEmoji, ReactionMenuOption] = None,
                    cancelEmoji: lib.emojis.BasedEmoji = cfg.defaultEmojis.cancel,
                    titleTxt: str = "", desc: str = "", col: Colour = Colour.blue(), timeout: TimedTask = None,
                    footerTxt: str = "", img: str = "", thumb: str = "", icon: str = "", authorName: str = "",
                    targetMember: Member = None, targetRole: Role = None):
        """
        :param discord.Message msg: the message where this menu is embedded
        :param options: A dictionary storing all of the menu's options and their behaviour (Default {})
        :type options: dict[lib.emojis.BasedEmoji, ReactionMenuOption]
        :param lib.emojis.BasedEmoji emoji: The emoji members should react with to cancel the menu.
                                            (Default cfg.defaultEmojis.cancel)
        :param str titleTxt: The content of the embed title (Default "")
        :param str desc: he content of the embed description; appears at the top below the title (Default "")
        :param discord.Colour col: The colour of the embed's side strip (Default None)
        :param str footerTxt: Secondary description appearing in darker font at the bottom of the embed
                                (Default time until menu expiry if timeout is not None, "" otherwise)
        :param str img: URL to a large icon appearing as the content of the embed, left aligned like a field (Default "")
        :param str thumb: URL to a larger image appearing to the right of the title (Default "")
        :param str icon: URL to a smaller image to the left of authorName. AuthorName is required
                        for this to be displayed. (Default "")
        :param str authorName: Secondary, smaller title for the embed (Default "")
        :param TimedTask timeout: The TimedTask responsible for expiring this menu (Default None)
        :param discord.Member targetMember: The only discord.Member that is able to interact with this menu.
                                            All other reactions are ignored (Default None)
        :param discord.Role targetRole: In order to interact with this menu, users must possess this role.
                                        All other reactions are ignored (Default None)
        """
        self.cancelEmoji = cancelEmoji
        options[cancelEmoji] = NonSaveableReactionMenuOption("cancel", cancelEmoji, self.delete, None)
        super(CancellableReactionMenu, self).__init__(msg, options=options, titleTxt=titleTxt, desc=desc, col=col,
                                                        footerTxt=footerTxt, img=img, thumb=thumb, icon=icon,
                                                        authorName=authorName, timeout=timeout, targetMember=targetMember,
                                                        targetRole=targetRole)


    def toDict(self, **kwargs) -> dict:
        """Serializes the reaction menu to a dictionary representation.
        This currently does not add any information on top of ReactionMenu.toDict, but ensures that the cancel option
        is not included in the dictionary for space efficiency purposes.
        This function does not currently have an associated fromDict function, making this class unsaveable.
        To make this class saveable, extend it and create custom toDict and fromDict methods, with knowledge of
        what the option functionality will be.

        :return: A dictionary containing information about this menu, to be used when configuring a recreation of this object.
        :rtype: dict
        """
        baseDict = super(CancellableReactionMenu, self).toDict(**kwargs)
        # TODO: Make sure the option is in there?
        del baseDict["options"][self.cancelEmoji.sendable]

        return baseDict


class SingleUserReactionMenu(ReactionMenu):
    """An in-place menu solution.
    
    InlineReactionMenus do not need to be recorded in the reactionMenusDB, but instead have a
    doMenu coroutine which should be awaited. Once execution returns, doMenu will return a list containing all of the
    currently selected options.
    
    This menu style is only available for use by single users - hence the requirement for targetMember.
    returnTriggers is given as a kwarg, but if no returnTriggers are given, then the menu will only expire due ot timeout.

    :var returnTriggers: A list of emojis which, when reacted with, trigger the expiry of the menu.
    :vartype returnTriggers: List[lib.emojis.BasedEmoji]
    :var timeoutSeconds: The number of seconds that this menu should last before timing out
    :vartype timeoutSeconds: int
    """

    def __init__(self, msg: Message, targetMember: Union[Member, User], timeoutSeconds: int,
                 options: Dict[lib.emojis.BasedEmoji, ReactionMenuOption] = None,
                 returnTriggers: List[lib.emojis.BasedEmoji] = [], titleTxt: str = "", desc: str = "",
                 col: Colour = Colour.blue(), footerTxt: str = "", img: str = "", thumb: str = "",
                 icon: str = "", authorName: str = ""):
        """
        :param returnTriggers: A list of emojis which, when reacted with, trigger the expiry of the menu.
        :type returnTriggers: List[lib.emojis.BasedEmoji]
        :param int timeoutSeconds: The number of seconds that this menu should last before timing out
        """
        if footerTxt == "":
            footerTxt = "This menu will expire in " + str(timeoutSeconds) + " seconds."
        super().__init__(msg, targetMember=targetMember, options=options, titleTxt=titleTxt, desc=desc, col=col,
                            footerTxt=footerTxt, img=img, thumb=thumb, icon=icon, authorName=authorName)
        self.returnTriggers = returnTriggers
        self.timeoutSeconds = timeoutSeconds


    def reactionClosesMenu(self, reactPL: RawReactionActionEvent) -> bool:
        """Decide whether a reaction should trigger the expiry of the menu.
        The reaction should be given in the form of a RawReactionActionEvent payload, from a discord.on_raw_reaction_add event

        :param discord.RawReactionActionEvent reactPL: The raw payload representing the reaction addition
        :return: True if the reaction should close the menu. I.e, a returnTrigger emoji was added by the targetMember.
        :rtype: bool
        """
        try:
            return (reactPL.message_id == self.msg.id and reactPL.user_id == self.targetMember.id) and \
                    (not self.returnTriggers or lib.emojis.BasedEmoji.fromPartial(reactPL.emoji) in self.returnTriggers)
        except lib.exceptions.UnrecognisedCustomEmoji:
            return False


    async def doMenu(self) -> List[lib.emojis.BasedEmoji]:
        """Coroutine that executes the menu.

        Once execution returns to the calling thread, doMenu will have returned a list of emojis that
        are currently selected by the targetMember. If your option behaviour removes any reactions,
        these will not be present in the returned list.

        :return: A list of emojis with which targetMember has reacted to the member with, at the time of expiry.
        :rtype: List[lib.emojis.BasedEmoji]
        """
        await self.updateMessage()
        try:
            await botState.client.wait_for("raw_reaction_add", check=self.reactionClosesMenu, timeout=self.timeoutSeconds)
            currentEmbed = self.msg.embeds[0]
            currentEmbed.set_footer(text="This menu has now expired.")
            await self.msg.edit(embed=currentEmbed)
        except asyncio.TimeoutError:
            await self.msg.edit(content="This menu has now expired. Please try the command again.")
            return []
        else:
            updatedMsg = await self.msg.channel.fetch_message(self.msg.id)
            return [lib.emojis.BasedEmojiFromReaction(react.emoji) for react in updatedMsg.reactions \
                    if self.targetMember in await react.users().flatten() and \
                    lib.emojis.BasedEmojiFromReaction(react.emoji) in self.options]
