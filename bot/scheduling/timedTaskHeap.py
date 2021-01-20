from . import timedTask
from heapq import heappop, heappush
import inspect
from types import FunctionType


class TimedTaskHeap:
    """A min-heap of TimedTasks, sorted by task expiration time.
    TODO: Return a value from the expiryFunction in case someone wants to use that

    :var tasksHeap: The heap, stored as an array. tasksHeap[0] is always the TimedTask with the closest expiry time.
    :vartype tasksHeap: list[TimedTask]
    :var expiryFunction: function reference to call upon the expiry of any TimedTask managed by this heap.
    :vartype expiryFunction: FunctionType
    :var hasExpiryFunction: Whether or not this heap has an expiry function to call
    :vartype hasExpiryFunction: bool
    :var expiryFunctionArgs: an object to pass to expiryFunction when calling. There is no type requirement,
                                but a dictionary is recommended as a close representation of KWArgs.
    :var hasExpiryFunctionArgs: Whether or not the expiry function has args to pass
    :vartype hasExpiryFunctionArgs: bool
    :var asyncExpiryFunction: whether or not the expiryFunction is a coroutine and needs to be awaited
    :vartype asyncExpiryFunction: bool
    """

    def __init__(self, expiryFunction: FunctionType = None, expiryFunctionArgs = None):
        """
        :param function expiryFunction: function reference to call upon the expiry of any
                                        TimedTask managed by this heap. (Default None)
        :param expiryFunctionArgs: an object to pass to expiryFunction when calling. There is no type requirement,
                                    but a dictionary is recommended as a close representation of KWArgs. (Default {})
        """
        self.tasksHeap = []

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
