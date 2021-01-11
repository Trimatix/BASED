# TODO: Remake most of these with regex

def isInt(x) -> bool:
    """Decide whether or not something is either an integer, or is castable to integer.

    :param x: The object to type-check
    :return: True if x is an integer or if x can be casted to integer. False otherwise
    :rtype: bool
    """

    try:
        int(x)
    except TypeError:
        return False
    except ValueError:
        return False
    return True


def isMention(mention: str) -> bool:
    """Decide whether the given string is a discord user mention,
    being either <@USERID> or <@!USERID> where USERID is an integer discord user id.

    :param str mention: The string to check
    :return: True if mention matches the formatting of a discord user mention, False otherwise
    :rtype: bool
    """
    return mention.endswith(">") and ((mention.startswith("<@") and isInt(mention[2:-1])) or \
                                        (mention.startswith("<@!") and isInt(mention[3:-1])))


def isRoleMention(mention: str) -> bool:
    """Decide whether the given string is a discord role mention, being <@&ROLEID> where ROLEID is an integer discord role id.

    :param str mention: The string to check
    :return: True if mention matches the formatting of a discord role mention, False otherwise
    :rtype: bool
    """
    return mention.endswith(">") and mention.startswith("<@&") and isInt(mention[3:-1])


def commaSplitNum(num: str) -> str:
    """Insert commas into every third position in a string.
    For example: "3" -> "3", "30000" -> "30,000", and "561928301" -> "561,928,301"

    :param str num: string to insert commas into. probably just containing digits
    :return: num, but split with commas at every third digit
    :rtype: str
    """
    outStr = num
    for i in range(len(num), 0, -3):
        outStr = outStr[0:i] + "," + outStr[i:]
    return outStr[:-1]


# string extensions for numbers, e.g 11th, 1st, 23rd...
numExtensions = ["th", "st", "nd", "rd", "th", "th", "th", "th", "th", "th"]


def getNumExtension(num: int) -> str:
    """Return the string extension for an integer, e.g 'th' or 'rd'.

    :param int num: The integer to find the extension for
    :return: string containing a number extension from numExtensions
    :rtype: str
    """
    return numExtensions[int(str(num)[-1])] if not (num > 10 and num < 20) else "th"
