from typing import Protocol, TypeVar, Type, Union, Mapping
import json
from carica import SerializableType, PrimativeType, SerializesToDict
from carica.exceptions import NonSerializableObject
from pathlib import Path

TSelf = TypeVar("TSelf", bound="SerializesToDict")
JsonType = Mapping[str, PrimativeType]

class AsyncSerializesToDict(Protocol):
    async def serialize(self, **kwargs) -> JsonType: ...

    @classmethod
    async def deserialize(cls: Type[TSelf], data: JsonType, **kwargs) -> TSelf: ...


def readJSON(dbFile: Union[Path, str]) -> JsonType:
    """Read the json file with the given path, and return the contents as a dictionary.

    :param str dbFile: Path to the file to read
    :return: The contents of the requested json file, parsed into a python dictionary
    :rtype: dict 
    """
    f = open(dbFile, "r")
    txt = f.read()
    f.close()
    return json.loads(txt)


def writeJSON(dbFile: Union[Path, str], db: JsonType, prettyPrint=False):
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
    f.write(txt)
    f.close()


T = TypeVar("T", bound=SerializableType)


def loadObject(filePath: Union[Path, str], objectType: Type[T], **kwargs) -> T:
    """Read the specified JSON file, and deserialize the contents into a new instance of `objectType`.

    :param str filePath: path to the JSON file to save to. Theoretically, this can be absolute or relative.
    :param objectType: the object type to deserialize `filePath`'s contents into
    """
    if not issubclass(objectType, SerializableType):
        raise NonSerializableObject(objectType)
    
    data = readJSON(filePath)
    return objectType.deserialize(data, **kwargs)


def saveObject(filePath: Union[Path, str], o: SerializesToDict, **kwargs):
    """Call the given serializable object's serialize method, and save the resulting dictionary to the specified JSON file.

    :param str filePath: path to the JSON file to save to. Theoretically, this can be absolute or relative.
    :param o: the object to save
    """
    if not isinstance(o, SerializableType):
        raise NonSerializableObject(o)
    writeJSON(filePath, o.serialize(**kwargs))


def saveObjectAsync(filePath: Union[Path, str], o: AsyncSerializesToDict, **kwargs):
    """This function should be used in place of saveObject for objects whose serialize method is asynchronous.
    This function is currently unused.

    Await the given object's serialize method, and save the resulting dictionary to the specified JSON file.

    :param str filePath: path to the JSON file to save to. Theoretically, this can be absolute or relative.
    :param o: the object to save
    """
    if not isinstance(o, SerializableType):
        raise NonSerializableObject(o)
    return _saveObjectAsync(filePath, o, **kwargs)


async def _saveObjectAsync(filePath: Union[Path, str], o: AsyncSerializesToDict, **kwargs):
    data = await o.serialize(**kwargs)
    writeJSON(filePath, data)
