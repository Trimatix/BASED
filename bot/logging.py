from .cfg import cfg
from os import path
from datetime import datetime
import traceback
from typing import Tuple


LOG_TIME_FORMAT = "(%d/%m/%H:%M)"


class Logger:
    """A general event logging object.
    Takes strings describing events, categorises them, sorts them by time added,
    and saves them to separate text files by category. Upon saving to file, the logger clears its logs.
    TODO: Add option to save to tsv or similar instead of txt

    :var logs: A dictionary associating category names with dictionaries, associating datetime.datetimes with event strings
    :vartype logs: dict[str, dict[datetime.datetime, str]]
    """

    def __init__(self):
        self.clearLogs()


    def clearLogs(self):
        """Clears all logs from the database.
        """
        self.logs = {"usersDB": {}, "guildsDB": {}, "reactionMenus": {}, "misc": {}}


    def isEmpty(self) -> bool:
        """Decide whether or not any logs are currently stored, waiting to be saved to file.

        :return: False if any of the logger's categories currently contains any logs. True otherwise.
        :rtype: bool
        """
        for cat in self.logs:
            if bool(self.logs[cat]):
                return False
        return True


    def peekHeadTimeAndCategory(self) -> Tuple[datetime, str]:
        """Get the log time of the earliest-logged event currently stored in the logger, as well as the category of the event.
        If the logger is currently empty, None is returned as the log time, and "" as the category.

        :return: If the logger is not empty, a tuple whose first element is the time that the earliest-logged event was
                added to the logger, and whose second element is the earliest-logged event's category. (None, "") otherwise.
        :rtype: tuple[datetime.datetime or None, str]
        """
        head, headCat = None, ""
        for cat in self.logs:
            if bool(self.logs[cat]):
                currHead = list(self.logs[cat].keys())[0]
                if head is None or currHead < head:
                    head, headCat = currHead, cat

        return head, headCat


    def popHeadLogAndCategory(self) -> Tuple[str, str]:
        """Pop the earliest-logged event and its category. This also removes the returned log from the logger.
        If the logger is currently empty, ("", "") is returned.

        :return: If the logger is not empty, a tuple whose first element is the event string of the earliest-logged event,
                and whose second element is that log's category. ("", "") otherwise.
        :rtype: tuple[str, str]
        """
        head, headCat = self.peekHeadTimeAndCategory()

        if head is None:
            log = ""
        else:
            log = self.logs[headCat][head]
            del self.logs[headCat][head]

        return log, headCat


    def save(self):
        """Save all currently stored logs to separate text files, named after categories.
        Log files are saved to the directory specified in cfg.paths.logsFolder.
        Logs are sorted by the time they were added to the logger prior to saving.
        After saving, the logger is cleared of logs.
        If category-named text files do not exist, they are created.

        ⚠ If exceptions are encountered when attempting to save logs,
        the exceptions themselves are logged in the logger and printed to console.
        If the exceptions are not fixed externally prior to bot shutdown, this will result
        in all stored logs being lost.
        """
        if self.isEmpty():
            return

        logsSaved = ""
        files = {}
        nowStr = datetime.utcnow().strftime(LOG_TIME_FORMAT)

        for category in self.logs:
            if bool(self.logs[category]):
                currentFName = cfg.paths.logsFolder + ("" if cfg.paths.logsFolder.endswith("/") else "/") + category + ".txt"
                logsSaved += category + ".txt, "

                if category not in files:
                    if not path.exists(currentFName):
                        try:
                            f = open(currentFName, 'xb')
                            f.close()
                            logsSaved += "[+]"
                        except IOError as e:
                            print(nowStr + "-[LOG::SAVE]>F_NEW_IOERR: ERROR CREATING LOG FILE: " +
                                  currentFName + ":" + e.__class__.__name__ + "\n" + traceback.format_exc())
                    try:
                        files[category] = open(currentFName, 'ab')
                    except IOError as e:
                        print(nowStr + "-[LOG::SAVE]>F_OPN_IOERR: ERROR OPENING LOG FILE: " +
                              currentFName + ":" + e.__class__.__name__ + "\n" + traceback.format_exc())
                        files[category] = None

        while not self.isEmpty():
            log, category = self.popHeadLogAndCategory()
            if files[category] is not None:
                try:
                    # log strings first encoded to bytes (utf-8) to allow for unicode chars
                    files[category].write(log.encode())
                except IOError as e:
                    print(nowStr + "-[LOG::SAVE]>F_WRT_IOERR: ERROR WRITING TO LOG FILE: " +
                          files[category].name + ":" + e.__class__.__name__ + "\n" + traceback.format_exc())
                except UnicodeEncodeError as e:
                    print(e.start)

        for f in files.values():
            f.close()
        if logsSaved != "":
            print(nowStr + "-[LOG::SAVE]>SAVE_DONE: Logs saved: " + logsSaved[:-2])

        self.clearLogs()


    def log(self, classStr: str, funcStr: str, event: str, category: str = "misc",
            eventType: str = "MISC_ERR", trace: str = "", noPrintEvent: bool = False, noPrint: bool = False):
        """Log an event, queueing the log to be saved to a file.

        :param str classStr: The class in which the event occurred
        :param str funcStr: The function in which the event occurred
        :param str event: The event string - a string describing the event that occurred.
        :param str category: The category of the event, corresponding to the name of the log file where this event will
                            be saved. Must match one of the keys in ths logger's logs dictionary. (Default 'misc')
        :param str eventType: The type of event, analagous to an exception type name. (Default 'MISC_ERR')
        :param str trace: If the logged event is an exception, you may wish to provide a stack trace
                            here with traceback.format_exc(). (Default "")
        :param bool noPrintEvent: Give True to print this log to console without the event string. Useful in cases where
                            the event string is very long. (Default False)
        :param bool noPrint: Skip printing this log to console entirely. Useful in cases where the log occurrs frequently
                            and helps little with debugging or similar. (Default False)
        """
        if category not in self.logs:
            self.log("misc", "Log", "log", "ATTEMPTED TO LOG TO AN UNKNOWN CATEGORY '" +
                     str(category) + "' -> Redirected to misc.", eventType="UNKWN_CTGR")

        now = datetime.utcnow()
        if noPrintEvent:
            eventStr = now.strftime(LOG_TIME_FORMAT) + "-[" + str(classStr).upper() + \
                "::" + str(funcStr).upper() + "]>" + str(eventType)
            if not noPrint:
                print(eventStr)
            self.logs[category][now] = eventStr + ": " + str(event) + ("\n" + trace if trace != "" else "") + "\n\n"
        else:
            eventStr = now.strftime(LOG_TIME_FORMAT) + "-[" + str(classStr).upper() + \
                "::" + str(funcStr).upper() + "]>" + str(eventType) + ": " + str(event)
            if not noPrint:
                print(eventStr)
            self.logs[category][now] = eventStr + ("\n" + trace if trace != "" else "") + "\n\n"
