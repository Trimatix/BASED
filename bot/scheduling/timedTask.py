from __future__ import annotations
from typing import Any, Callable, Coroutine, Optional, Union
from asyncio import Task, create_task
from datetime import datetime, timedelta

import discord

from .. import botState, lib

TTCallbackType = Union[Callable[[Any], Coroutine], Callable[[], Coroutine]]

class TimedTask:
    """A fairly generic class that, at its core, tracks when a requested amount of time has passed.
    Using an expiryFunction, a function call may be delayed by a given amount of time.
    Using autoRescheduling, this class can also be used to easily schedule reoccurring tasks.
    At least one of expiryTime or expiryDelta must be given.
    If the task is set to autoReschedule, issueTime is updated to show the task's current rescheduling time.
    :var issueTime: The datetime when this task was created.
    :vartype issueTime: datetime.datetime
    :var expiryTime: The datetime when this task should expire.
    :vartype expiryTime: datetime.datetime
    :var expiryDelta: The timedelta to add to issueTime, to find the expiryTime.
    :vartype expiryDelta: datetime.timedelta
    :var expiryFunction: The coroutine to call once expiryTime has been reached/surpassed. MUST be a coroutine.
    :vartype expiryFunction: TTCallbackType
    :var hasExpiryFunction: Whether or not the task has an expiry function to call
    :vartype hasExpiryFunction: bool
    :var expiryFunctionArgs: The data to pass to the expiryFunction. There is no type requirement,
                                but a dictionary is recommended as a close representation of KWArgs.
    :var hasExpiryFunctionArgs: Whether or not expiryFunction contains anything and should be passed to expiryFunction
    :vartype hasExpiryFunctionArgs: bool
    :var autoReschedule: Whether or not this task should automatically reschedule itself by the same timedelta.
    :vartype autoReschedule: bool
    :var gravestone: marked as True when the TimedTask will no longer execute and can be removed from any TimedTask heap.
                        I.e, it is expired (whether manually or through timeout) and does not auto-reschedule
    :vartype gravestone: bool
    :var rescheduleOnExpiryFuncFailure: Whether or not expiry exception throws should trigger the task to auto reschedule.
                                        Useful for delaying a task to retry later once a problem will be fixed
    :vartype rescheduleOnExpiryFuncFailure: bool
    """

    def __init__(self, issueTime : Optional[datetime] = None, expiryTime : Optional[datetime] = None, expiryDelta : Optional[timedelta] = None,
                 expiryFunction : Optional[TTCallbackType] = None, expiryFunctionArgs : Any = None, autoReschedule : bool = False,
                 rescheduleOnExpiryFuncFailure : bool = False):
        """
        :param datetime.datetime issueTime: The datetime when this task was created. (Default now)
        :param datetime.datetime expiryTime: The datetime when this task should expire. (Default None)
        :param datetime.timedelta expiryDelta: The timedelta to add to issueTime, to find the expiryTime. (Default None)
        :param TTCallbackType expiryFunction: The coroutine to call once expiryTime has been reached/surpassed. MUST be a coroutine. (Default None)
        :param expiryFunctionArgs: The data to pass to the expiryFunction. There is no type requirement,
                                    but a dictionary is recommended as a close representation of KWArgs. (Default {})
        :param bool autoReschedule: Whether or not this task should automatically reschedule itself by the
                                    same timedelta. (Default False)
        :param bool rescheduleOnExpiryFuncFailure: Whether or not expiry exception throws should trigger the task to
                                                    auto reschedule. Useful for delaying a task to retry later once a problem
                                                    will be fixed (Default False)
        """
        # Ensure that at least one of expiryTime or expiryDelta is specified
        if expiryTime is not None:
            self.expiryTime = expiryTime
        else:
            if expiryDelta is None:
                raise ValueError("No expiry time given, both expiryTime and expiryDelta are None")
            
            # Calculate expiryTime as issueTime + expiryDelta if none is given
            self.expiryTime = (self.issueTime + expiryDelta) if expiryTime is None else expiryTime

        # Calculate issueTime as now if none is given
        self.issueTime = discord.utils.utcnow() if issueTime is None else issueTime

        # Calculate expiryDelta as expiryTime - issueTime if none is given. This is needed for rescheduling.
        self.expiryDelta = (self.expiryTime - self.issueTime) if expiryDelta is None else expiryDelta

        self.expiryFunction = expiryFunction
        self.hasExpiryFunction = expiryFunction is not None
        self.hasExpiryFunctionArgs = expiryFunctionArgs is not None
        self.expiryFunctionArgs: Any = expiryFunctionArgs if self.hasExpiryFunctionArgs else {}
        self.autoReschedule = autoReschedule
        self.rescheduleOnExpiryFuncFailure = rescheduleOnExpiryFuncFailure

        # A task's 'gravestone' is marked as True when the TimedTask will no longer execute and
        # can be removed from any TimedTask heap. I.e, it is expired (whether manually or through timeout)
        # and does not auto-reschedule.
        self.gravestone = False


    def __lt__(self, other: TimedTask) -> bool:
        """< Overload, to be used in TimedTask heaps.
        The other object must be a TimedTask. Compares only the expiryTimes of the two tasks.
        :param TimedTask other: other TimedTask to compare against.
        :return: True if this TimedTask's expiryTime is < other's expiryTime, False otherwise.
        :rtype: bool
        """
        if not isinstance(other, TimedTask):
            raise TypeError("< error: TimedTask can only be compared to other TimedTasks")
        return self.expiryTime < other.expiryTime


    def __gt__(self, other: TimedTask) -> bool:
        """> Overload, to be used in TimedTask heaps.
        The other object must be a TimedTask. Compares only the expiryTimes of the two tasks.
        :param TimedTask other: other TimedTask to compare against.
        :return: True if this TimedTask's expiryTime is > other's expiryTime, False otherwise.
        :rtype: bool
        """
        if not isinstance(other, TimedTask):
            raise TypeError("> error: TimedTask can only be compared to other TimedTasks")
        return self.expiryTime > other.expiryTime


    def __lte__(self, other: TimedTask) -> bool:
        """<= Overload, to be used in TimedTask heaps.
        The other object must be a TimedTask. Compares only the expiryTimes of the two tasks.
        :param TimedTask other: other TimedTask to compare against.
        :return: True if this TimedTask's expiryTime is <= other's expiryTime, False otherwise.
        :rtype: bool
        """
        if not isinstance(other, TimedTask):
            raise TypeError("<= error: TimedTask can only be compared to other TimedTasks")
        return self.expiryTime <= other.expiryTime


    def __gte__(self, other: TimedTask) -> bool:
        """>= Overload, to be used in TimedTask heaps.
        The other object must be a TimedTask. Compares only the expiryTimes of the two tasks.
        :param TimedTask other: other TimedTask to compare against.
        :return: True if this TimedTask's expiryTime is >= other's expiryTime, False otherwise.
        :rtype: bool
        """
        if not isinstance(other, TimedTask):
            raise TypeError(">= error: TimedTask can only be compared to other TimedTasks")
        return self.expiryTime >= other.expiryTime


    def isExpired(self) -> bool:
        """Decide whether or not this task has expired.
        This can be due to reaching the task's expiryTime, or due to manual expiry.
        :return: True if this timedTask has been manually expired, or has reached its expiryTime. False otherwise
        :rtype: bool
        """
        self.gravestone = self.gravestone or self.expiryTime <= discord.utils.utcnow()
        return self.gravestone


    async def doTaskWithRescheduling(self, coro: Task):
        await coro
        if e := coro.exception():
            if self.rescheduleOnExpiryFuncFailure:
                botState.client.logger.log(type(self).__name__, "callExpiryFunction",
                                    f"Exception occured in callExpiryFunction {self.expiryFunction}, rescheduling: {self}.",
                                    exception=e, noPrint=True)
                self.reschedule()
            else:
                lib.discordUtil.logException(coro, e)
                raise e


    def callExpiryFunction(self):
        """Call the task's expiryFunction, if one is specified.
        Handles passing of arguments to the expiryFunction, if specified.
        If an exception occurs in the expiry function and rescheduleOnExpiryFuncFailure is True,
        the exception is IGNORED and the timedtask rescheduled.
        :return: the results of the expiryFunction
        """
        if self.expiryFunction is None: return
        # Pass args to expiry function if specified
        # ignoring warnings here due to arguments being incompatible with expiry function signature.
        # The signature is checked with hasExpiryFunctionArgs, so the call signature is correct.
        if self.hasExpiryFunctionArgs:
            create_task(self.doTaskWithRescheduling(create_task(self.expiryFunction(self.expiryFunctionArgs)))) # type: ignore[reportGeneralTypeIssues]
        else:
            create_task(self.doTaskWithRescheduling(create_task(self.expiryFunction()))) # type: ignore[reportGeneralTypeIssues]


    def doExpiryCheck(self, callExpiryFunc: bool = True) -> bool:
        """Function to be called regularly, that handles the expiry of this task.
        Handles calling of the task's expiry function if specified, and rescheduling of the task if specified.
        :param bool callExpiryFunc: Whether or not to call this task's expiryFunction if it is expired. Default: True
        :return: True if this task is expired in this check, False otherwise. Regardless of autorescheduling.
        :rtype: bool
        """
        expired = self.isExpired()
        # If the task has expired, call expiry function and reschedule if specified
        if expired:
            if callExpiryFunc and self.hasExpiryFunction:
                self.callExpiryFunction()
            if self.autoReschedule:
                self.reschedule()
        return expired


    def reschedule(self, expiryTime: Optional[datetime] = None, expiryDelta: Optional[timedelta] = None):
        """Reschedule this task, with the timedelta given/calculated on the task's creation,
        or to a given expiryTime/Delta. Rescheduling will update the task's issueTime to now.
        TODO: A firstIssueTime may be useful in the future to represent creation time.
        Giving an expiryTime or expiryDelta will not update the task's stored expiryDelta.
        I.e, if the task is rescheduled again without giving an expiryDelta,
        The expiryDelta given/calculated on the task's creation will be used.
        If both an expiryTime and an expiryDelta is given, the expiryTime takes precedence.
        :param datetime.datetime expiryTime: The new expiry time for the task. Default: now + expiryTime
                                                if expiryTime is specified, now + self.expiryTime otherwise
        :param datetime.timedelta expiryDelta: The amount of time to wait until the task's next expiry.
                                                Default: now + self.expiryTime
        """
        # Update the task's issueTime to now
        self.issueTime = discord.utils.utcnow()
        # Create the new expiryTime from now + expirydelta
        if expiryTime is not None:
            self.expiryTime = expiryTime
        else:
            self.expiryTime = self.issueTime + (self.expiryDelta if expiryDelta is None else expiryDelta)
        # reset the gravestone to False, in case the task had been expired and marked for removal
        self.gravestone = False


    def forceExpire(self, callExpiryFunc: bool = True):
        """Force the expiry of this task.
        Handles calling of this task's expiryFunction, and rescheduling if specified. Set's the task's expiryTime to now.
        :param bool callExpiryFunction: Whether or not to call the task's expiryFunction if the task expires. Default: True
        :return: The result of the expiry function, if it is called
        """
        # Update expiryTime
        self.expiryTime = discord.utils.utcnow()
        # Call expiryFunction and reschedule if specified
        if callExpiryFunc and self.hasExpiryFunction:
            expiryFuncResults = self.callExpiryFunction()
        else:
            expiryFuncResults = None

        if self.autoReschedule:
            self.reschedule()
        # Mark for removal if not rescheduled
        else:
            self.gravestone = True
        # Return expiry function results
        if callExpiryFunc and self.hasExpiryFunction:
            return expiryFuncResults


DelayGeneratorType = Union[Callable[[], timedelta], Callable[[Any], timedelta]]


class DynamicRescheduleTask(TimedTask):
    """A TimedTask which fetches the expiryDELTA (not time!) from a function, rather than actual arguments.
    This allows for dynamically choosing the reschedule time.
    If an expiryTime is specified, then this will be used for the first scheduling period. After this time is reached,
    the scheduler will switch to calling the delayTimeGenerator.
    :var delayTimeGenerator: Reference (not call!) to the function which generates the
                                expiryDelta. Must return a timedelta.
    :vartype delayTimeGenerator: function
    :var delayTimeGeneratorArgs: The data to pass to the delayTimeGenerator. There is no type requirement,
                                    but a dictionary is recommended as a close representation of KWArgs. (Default {})
    :var issueTime: The datetime when this task was created. (Default now)
    :vartype issueTime: datetime
    :var expiryTime: The datetime when this task should expire. (Default None)
    :vartype expiryTime: datetime
    :var expiryFunction: The function to call once expiryTime has been reached/surpassed. (Default None)
    :vartype expiryFunction: function
    :var expiryFunctionArgs: The data to pass to the expiryFunction. There is no type requirement,
                                but a dictionary is recommended as a close representation of KWArgs. (Default {})
    :var autoReschedule: Whether or not this task should automatically reschedule itself.
                            You probably want this to be True, otherwise you may as well use a TimedTask. (Default False)
    :varType autoReschedule: True
    """

    def __init__(self, delayTimeGenerator : DelayGeneratorType, initialDelta: Optional[timedelta] = None,
                        delayTimeGeneratorArgs : Any = None, issueTime : Optional[datetime] = None, expiryTime : Optional[datetime] = None,
                        expiryFunction : Optional[TTCallbackType] = None, expiryFunctionArgs : Any = None, autoReschedule : bool = False,
                        rescheduleOnExpiryFuncFailure : bool = False):
        """
        :param DelayGeneratorType delayTimeGenerator: Reference (not call!) to the function which generates the expiryDelta.
                                                        Must return a timedelta, and must be synchronous (not a coroutine)
        :param timedelta initialDelta: expiryDelta to use for the initial task scheduling. If delayTimeDenerator
                                        is a coroutine, this is a required argument. 
        :param delayTimeGeneratorArgs: The data to pass to the delayTimeGenerator. There is no type requirement, but a
                                        dictionary is recommended as a close representation of KWArgs. (Default {})
        :param datetime.datetime issueTime: The datetime when this task was created. (Default now)
        :param datetime.datetime expiryTime: The datetime when this task should expire. (Default None)
        :param DelayGeneratorType expiryFunction: The function to call once expiryTime has been reached/surpassed. (Default None)
        :param expiryFunctionArgs: The data to pass to the expiryFunction. There is no type requirement, but a dictionary
                                    is recommended as a close representation of KWArgs. (Default {})
        :param bool autoReschedule: Whether or not this task should automatically reschedule itself. You probably want this
                                    to be True, otherwise you may as well use a TimedTask. (Default False)
        :param bool rescheduleOnExpiryFuncFailure: Whether or not expiry exception throws should trigger the task to auto
                                                    reschedule. Useful for delaying a task to retry later once a problem will
                                                    be fixed (Default False)
        """
        self.delayTimeGenerator = delayTimeGenerator
        self.hasDelayTimeGeneratorArgs = delayTimeGeneratorArgs is not None
        self.delayTimeGeneratorArgs: Any = delayTimeGeneratorArgs if self.hasDelayTimeGeneratorArgs else {}
        initialDelta = initialDelta if initialDelta is not None else self.callDelayTimeGenerator()
        super(DynamicRescheduleTask, self).__init__(issueTime=issueTime, expiryTime=expiryTime, expiryDelta=initialDelta,
                                                    expiryFunction=expiryFunction, expiryFunctionArgs=expiryFunctionArgs,
                                                    autoReschedule=autoReschedule,
                                                    rescheduleOnExpiryFuncFailure=rescheduleOnExpiryFuncFailure)
        
        

    def callDelayTimeGenerator(self) -> timedelta:
        """Generate the next expiryTime using the delayTimeGenerator.
        :return: The results of delayTimeGenerator. Should be a timedelta.
        :rtype: datetime.timedelta
        """
        # Pass args to delayTimeGenerator if specified
        if self.hasDelayTimeGeneratorArgs:
            # Number of arguments is already checked for in specification of hasDelayTimeGeneratorArgs
            return self.delayTimeGenerator(self.delayTimeGeneratorArgs) # type: ignore
        else:
            # Number of arguments is already checked for in specification of hasDelayTimeGeneratorArgs
            return self.delayTimeGenerator() # type: ignore


    def reschedule(self):
        """Override. Start a new scheduling period for this task using the timedelta produced by delayTimeGenerator.
        """
        # Update the task's issueTime to now
        self.issueTime = discord.utils.utcnow()
        # Create the new expiryTime from now + delayTimeGenerator result
        self.expiryTime = self.issueTime + self.callDelayTimeGenerator()
        # reset the gravestone to False, in case the task had been expired and marked for removal
        self.gravestone = False
