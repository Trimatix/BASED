import traceback

def formatExceptionTrace(e: BaseException) -> str:
    """Formats the trace for an exception into a string.
    Great for debugging errors that are swallowed by the event loop.

    :param Exception e: The exception whose stack trace to format
    :return: The stack trace for e, formatted into a string
    :rtype: str
    """
    return "".join(traceback.format_exception(type(e), e, e.__traceback__))


class UnrecognisedCustomEmoji(Exception):
    """Exception raised when creating a BasedEmoji instance, but the client could not match an emoji to the given ID.

    :var id: The ID that coult not be matched
    :vartype id: int
    """

    def __init__(self, comment: str, id: int):
        """
        :param str comment: Description of the exception
        :param int id: The ID that coult not be matched
        """
        super().__init__(comment)
        self.id = id


class IncorrectCommandCallContext(Exception):
    """Exception used to indicate when a non-DMable command is called from DMs.
    May be used in the future to indicate the opposite; a command that can only be called from DMs is
    called from outside of DMs.
    """
    pass


class IncorrectInteractionContext(Exception):
    """Exception used to indicate when an interaction is triggered from somewhere it shouldn't, e.g in DMs,
    or in a non-messageable channel.
    """
    pass


class NoneDCGuildObj(Exception):
    """Raised when constructing a guild object, but the corresponding dcGuild was either not given or invalid.
    """
    pass


class NotReady(Exception):
    """Raised when attempting to perform an action on the client when the client is not ready yet.
    E.g:
    - databases not loaded yet
    - client not logged in yet
    """
    pass


class ClientInitFailed(Exception):
    """Raised when initialization of the discord client fails.
    """
    def __init__(self, inner: Exception) -> None:
        self.inner = inner
        super().__init__("Initialization of the discord client failed due to the following exception:\n" \
                        + formatExceptionTrace(inner))
