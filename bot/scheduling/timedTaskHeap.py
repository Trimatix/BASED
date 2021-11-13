from . import timedTask
from heapq import heappop, heappush
import inspect
from typing import Any, List, Union
import asyncio
from datetime import datetime


class TimedTaskHeap:
    """A min-heap of TimedTasks, sorted by task expiration time.
    TODO: Return a value from the expiryFunction in case someone wants to use that
    :var tasksHeap: The heap, stored as an array. tasksHeap[0] is always the TimedTask with the closest expiry time.
    :vartype tasksHeap: list[TimedTask]
    :var expiryFunction: function reference to call upon the expiry of any TimedTask managed by this heap.
    :vartype expiryFunction: timedTask.TTCallbackType
    :var hasExpiryFunction: Whether or not this heap has an expiry function to call
    :vartype hasExpiryFunction: bool
    :var expiryFunctionArgs: an object to pass to expiryFunction when calling. There is no type requirement,
                                but a dictionary is recommended as a close representation of KWArgs.
    :var hasExpiryFunctionArgs: Whether or not the expiry function has args to pass
    :vartype hasExpiryFunctionArgs: bool
    :var asyncExpiryFunction: whether or not the expiryFunction is a coroutine and needs to be awaited
    :vartype asyncExpiryFunction: bool
    """

    def __init__(self, expiryFunction : timedTask.TTCallbackType = None, expiryFunctionArgs : Any = None):
        """
        :param function expiryFunction: function reference to call upon the expiry of any
                                        TimedTask managed by this heap. (Default None)
        :param expiryFunctionArgs: an object to pass to expiryFunction when calling. There is no type requirement,
                                    but a dictionary is recommended as a close representation of KWArgs. (Default {})
        """
        self.tasksHeap: List[timedTask.TimedTask] = []

        self.expiryFunction = expiryFunction
        self.hasExpiryFunction = expiryFunction is not None
        self.hasExpiryFunctionArgs = expiryFunctionArgs is not None
        self.expiryFunctionArgs = expiryFunctionArgs if self.hasExpiryFunctionArgs else {}

        # Track whether or not the expiryFunction is a coroutine and needs to be awaited
        self.asyncExpiryFunction = inspect.iscoroutinefunction(expiryFunction)


    def cleanHead(self):
        """Remove expired tasks from the head of the heap.
        A task's 'gravestone' represents the task no longer being able to be called.
        I.e, it is expired (whether manually or through timeout) and does not auto-reschedule.
        """
        while len(self.tasksHeap) > 0 and self.tasksHeap[0].gravestone:
            heappop(self.tasksHeap)


    def scheduleTask(self, task: timedTask.TimedTask):
        """Schedule a new task onto this heap.
        :param TimedTask task: the task to schedule
        """
        heappush(self.tasksHeap, task)


    def unscheduleTask(self, task: timedTask.TimedTask):
        """Forcebly remove a task from the heap without 'expiring' it - no expiry functions or auto-rescheduling are called.
        This method overrides task autoRescheduling, forcibly removing the task from the heap entirely.
        :param TimedTask task: the task to remove from the heap
        """
        task.gravestone = True
        self.cleanHead()


    async def callExpiryFunction(self):
        """Call the HEAP's expiry function - not a task expiry function.
        Accounts for expiry function arguments (if specified) and asynchronous expiry functions
        TODO: pass down whatever the expiry function returns
        """
        # Await coroutine asynchronous functions
        if self.asyncExpiryFunction:
            # Pass args to the expiry function, if they are specified
            if self.hasExpiryFunctionArgs:
                await self.expiryFunction(self.expiryFunctionArgs)
            else:
                await self.expiryFunction()
        # Do not await synchronous functions
        else:
            # Pass args to the expiry function, if they are specified
            if self.hasExpiryFunctionArgs:
                self.expiryFunction(self.expiryFunctionArgs)
            else:
                self.expiryFunction()


    async def doTaskChecking(self):
        """Function to be called regularly (ideally in a main loop), that handles the expiring of tasks.
        Tasks are checked against their expiry times and manual expiry.
        Task and heap-level expiry functions are called upon task expiry, if they are defined.
        Tasks are rescheduled if they are marked for auto-rescheduling.
        Expired, non-rescheduling tasks are removed from the heap.
        """
        # Is the task at the head of the heap expired?
        while len(self.tasksHeap) > 0 and (self.tasksHeap[0].gravestone or await self.tasksHeap[0].doExpiryCheck()):
            # Call the heap's expiry function
            if self.hasExpiryFunction:
                await self.callExpiryFunction()
            # Remove the expired task from the heap
            task = heappop(self.tasksHeap)
            # push autorescheduling tasks back onto the heap
            if not task.gravestone:
                heappush(self.tasksHeap, task)


def startSleeper(delay: int, loop: asyncio.AbstractEventLoop, result: bool = None) -> asyncio.Task:
    async def _start(delay, loop, result=None):
        coro = asyncio.sleep(delay, result=result, loop=loop)
        task = asyncio.create_task(coro)
        try:
            return await task
        except asyncio.CancelledError:
            return result

    return loop.create_task(_start(delay, loop, result=result))


class AutoCheckingTimedTaskHeap(TimedTaskHeap):
    """A TimedTaskHeap that spawns a new thread to periodically perform expiry checking for you.
    Sleeping between task checks is handled by asyncio.sleep-ing precicely to the expiry time of the
    next closest task - found at the head of the heap.
    When a new task is scheduled onto the heap, its expiry time is compared with the task at the head of the heap.
    If it expires sooner, the expiry checking thread's sleep is cancelled, the task is placed at the head of the heap,
    and the expiry checking thread is restarted, automatically sleeping to the new expiry at the head of the heap.
    :var tasksHeap: The heap, stored as an array. tasksHeap[0] is always the TimedTask with the closest expiry time.
    :vartype tasksHeap: List[TimedTask]
    :var expiryFunction: function reference to call upon the expiry of any TimedTask managed by this heap.
    :vartype expiryFunction: timedTask.TTCallbackType
    :var hasExpiryFunction: Whether or not this heap has an expiry function to call
    :vartype hasExpiryFunction: bool
    :var expiryFunctionArgs: an object to pass to expiryFunction when calling. There is no type requirement,
                                but a dictionary is recommended as a close representation of KWArgs.
    :var hasExpiryFunctionArgs: Whether or not the expiry function has args to pass
    :vartype hasExpiryFunctionArgs: bool
    :var asyncExpiryFunction: whether or not the expiryFunction is a coroutine and needs to be awaited
    :vartype asyncExpiryFunction: bool
    :var active: Whether or not the heap is actively checking tasks
    :vartype active: bool
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, expiryFunction: timedTask.TTCallbackType = None, expiryFunctionArgs = None):
        """
        :param asyncio.AbstractEventLoop loop: The event loop to schedule the heap into
        :param function expiryFunction: function reference to call upon the expiry of any
                                        TimedTask managed by this heap. (Default None)
        :param expiryFunctionArgs: an object to pass to expiryFunction when calling. There is no type requirement,
                                    but a dictionary is recommended as a close representation of KWArgs. (Default {})
        """
        super().__init__(expiryFunction=expiryFunction, expiryFunctionArgs=expiryFunctionArgs)
        self.loop = loop
        self.active = False
        self.checkingLoopFuture: Union[None, asyncio.Future] = None
        self.sleepTask: Union[None, asyncio.Task] = None


    async def _checkingLoop(self):
        """The TimedTask expiry loop.
        Yields the thread until the soonest-expiring task's expiry time, expires the soonest task, rinse and repeat.
        If the heap is emptied of tasks, the loop becomes inactive, and the loop exists - If the heap empties
        and you wish to schedule a new task onto the heap, you must start a new checking loop as shown in scheduleTask.
        """
        while self.active:
            if len(self.tasksHeap) > 0:
                sleepDelta = self.tasksHeap[0].expiryTime - datetime.utcnow()
                coro = asyncio.sleep(sleepDelta.total_seconds(), loop=self.loop)
                self.sleepTask = asyncio.create_task(coro)

                try:
                    await self.sleepTask
                except asyncio.CancelledError:
                    pass
                else:
                    await self.doTaskChecking()

            else:
                self.sleepTask = None
                self.active = False


    def startTaskChecking(self):
        """Create the heap's task checking thread.
        """
        if self.active:
            raise RuntimeError("loop already active")
        self.active = True
        self.checkingLoopFuture = asyncio.create_task(self._checkingLoop())


    def stopTaskChecking(self):
        """Cancel the heap's task checking thread.
        """
        if self.active:
            self.active = False
            self.sleepTask.cancel()
            self.sleepTask = None
            self.checkingLoopFuture.cancel()


    def scheduleTask(self, task: timedTask.TimedTask, startLoop: bool = True):
        """Schedule a new task onto the heap.
        If no checking loop is currently active, a new one is started.
        If a checking loop is already active and waiting for task that expires after this one,
        the loop's current waiting time is updated to expire this task first.
        :param TimedTask task: the task to schedule
        :param bool startLoop: Give False here to override the starting of a new loop. This may be useful when creating
                                a new AutoCheckingTimedTaskheap with a large number of starting tasks, after which you start
                                the checking loop manually. In most cases though, this should be left at True. (Default True)
        """
        if self.active:
            if len(self.tasksHeap) > 0:
                soonest: Union[None, timedTask.TimedTask] = self.tasksHeap[0]
            else:
                soonest = None

            super().scheduleTask(task)
            
            if soonest is not None and task < soonest and self.sleepTask is not None:
                self.sleepTask.cancel()
                self.sleepTask = None
        else:
            super().scheduleTask(task)
            if startLoop:
                self.startTaskChecking()


    def unscheduleTask(self, task: timedTask.TimedTask):
        """Forcebly remove a task from the heap without 'expiring' it - no expiry functions or auto-rescheduling are called.
        This method overrides task autoRescheduling, forcibly removing the task from the heap entirely.
        If a checking loop is running and waiting for this task, the checking loop is updated to wait for the next
        available task.
        :param TimedTask task: the task to remove from the heap
        """
        if self.active and self.sleepTask is not None and len(self.tasksHeap) > 0 and task == self.tasksHeap[0]:
            self.sleepTask.cancel()
            self.sleepTask = None

        super().unscheduleTask(task)
