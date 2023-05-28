import json
import os


def readJSON(dbFile: str) -> dict:
    """Read the json file with the given path, and return the contents as a dictionary.

    :param str dbFile: Path to the file to read
    :return: The contents of the requested json file, parsed into a python dictionary
    :rtype: dict 
    """
    f = open(dbFile, "r")
    txt = f.read()
    f.close()
    return json.loads(txt)


def writeJSON(dbFile: str, db: dict, prettyPrint=False):
    """Write the given json-serializable dictionary to the given file path.
    All objects in the dictionary must be JSON-serializable.

    :param str dbFile: Path to the file which db should be written to
    :param dict db: The json-serializable dictionary to write
    :param bool prettyPrint: When False, write minified JSON. When true, write JSON with basic pretty printing (indentation)
    """
    if prettyPrint:
        txt = json.dumps(db, indent=4, sort_keys=True)
    else:
        txt = json.dumps(db)
    f = open(dbFile, "w")
    txt = f.write(txt)
    f.close()


def saveDB(dbPath: str, db, **kwargs):
    """Call the given database object's toDict method, and save the resulting dictionary to the specified JSON file.
    TODO: child database classes to a single ABC, and type check to that ABC here before saving

    :param str dbPath: path to the JSON file to save to. Theoretically, this can be absolute or relative.
    :param db: the database object to save
    """
    writeJSON(dbPath, db.toDict(**kwargs))


async def saveDBAsync(dbPath: str, db, **kwargs):
    """This function should be used in place of saveDB for database objects whose toDict method is asynchronous.
    This function is currently unused.

    Await the given database object's toDict method, and save the resulting dictionary to the specified JSON file.
    TODO: child database classes to a single ABC, and type check to that ABC here before saving

    :param str dbPath: path to the JSON file to save to. Theoretically, this can be absolute or relative.
    :param db: the database object to save
    """
    writeJSON(dbPath, await db.toDict(**kwargs))
