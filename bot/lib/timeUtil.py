from datetime import timedelta
from typing import Dict


def td_format_noYM(td_object: timedelta) -> str:
    """Create a string describing the attributes of a given datetime.timedelta object, in a
    human reader-friendly format.
    This function does not create 'week', 'month' or 'year' strings, its highest time denominator is 'day'.
    Any time denominations that are equal to zero will not be present in the string.

    :param datetime.timedelta td_object: The timedelta to describe
    :return: A string describing td_object's attributes in a human-readable format
    :rtype: str
    """
    seconds = int(td_object.total_seconds())
    periods = [
        ('day', 60 * 60 * 24),
        ('hour', 60 * 60),
        ('minute', 60),
        ('second', 1)
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            has_s = 's' if period_value > 1 else ''
            strings.append("%s %s%s" % (period_value, period_name, has_s))

    return ", ".join(strings)


def timeDeltaFromDict(timeDict: dict) -> timedelta:
    """Construct a datetime.timedelta from a dictionary,
    transforming keys into keyword arguments for the timedelta constructor.

    :param dict timeDict: dictionary containing measurements for each time interval. i.e weeks, days, hours, minutes,
                            seconds, microseconds and milliseconds. all are optional and case sensitive.
    :return: a timedelta with all of the attributes requested in the dictionary.
    :rtype: datetime.timedelta
    """
    return timedelta(weeks=timeDict["weeks"] if "weeks" in timeDict else 0,
                     days=timeDict["days"] if "days" in timeDict else 0,
                     hours=timeDict["hours"] if "hours" in timeDict else 0,
                     minutes=timeDict["minutes"] if "minutes" in timeDict else 0,
                     seconds=timeDict["seconds"] if "seconds" in timeDict else 0,
                     microseconds=timeDict["microseconds"] if "microseconds" in timeDict else 0,
                     milliseconds=timeDict["milliseconds"] if "milliseconds" in timeDict else 0)
