from typing import Dict, List, Union, overload
import string

_idToIndex: Dict[str, int] = {c: i for i, c in enumerate(string.printable)}
_indexToID: Dict[int, str] = {i: c for c, i in _idToIndex.items()}
_numChars = len(_idToIndex)

def _idCharToIndex(c: str, exclusions: List[str] = None) -> int:
    v = _idToIndex[c]
    if exclusions:
        if c in exclusions:
            raise ValueError("Cannot convert an excluded character")
        v -= sum(1 for i in exclusions if _idToIndex[i] < v)
    return v


def _indexToCharID(i: int, exclusions: List[str] = None) -> str:
    if exclusions is not None:
        i -= sum(1 for c in exclusions if _idToIndex[c] < i)
    v = _indexToID.get(i, None)
    if v is None:
        raise ValueError("index too big to convert")
    return v


def idToIndex(ID: str, exclusions: List[str] = None) -> int:
    """Convert a compacted ID from `indexToID` back into the original number.
    This method effectively converts `i` to a higher base, but allows for exclusions of characters
    from the alphabet.
    In order to convert correctly, if any exclusions were provided in `indexToID`, the same exclusions
    must be given here.

    :param ID: The ID to convert back to a number
    :type ID: str
    :param exclusions: A list of characters to exclude from the alphabet, defaults to None
    :type exclusions: List[str], optional
    :raises ValueError: If `'0'` is included in `exclusions`
    :return: The base 10 number that `ID` represents
    :rtype: int
    """
    numberBase = _numChars
    if exclusions is not None:
        if "0" in exclusions:
            raise ValueError("Cannot exclude reserved character '0'")
        numberBase -= len(exclusions)
    v = 0
    for i, c in enumerate(reversed(ID)):
        if c != "0":
            v += _idCharToIndex(c, exclusions=exclusions) * (numberBase ** i)
    return v


def indexToID(i: int, pad: int = None, exclusions: List[str] = None) -> str:
    """Compact a number into a much smaller string ID. This method effectively
    converts `i` to a higher base, but allows for exclusions of characters from the alphabet.

    :param i: The number to convert
    :type i: int
    :param pad: An amount to pad the result by, with zeros, defaults to None
    :type pad: int, optional
    :param exclusions: A list of characters to exclude from the alphabet, defaults to None
    :type exclusions: List[str], optional
    :raises ValueError: If `i` is less than 0
    :raises ValueError: If `'0'` is included in `exclusions`
    :return: A string that can be converted back to `i` with `idToIndex` (with your exclusions)
    :rtype: str
    """
    if i < 0:
        raise ValueError("index cannot be negative")
    
    if i > 0:
        numberBase = _numChars
        if exclusions is not None:
            if "0" in exclusions:
                raise ValueError("Cannot exclude reserved character '0'")
            numberBase -= len(exclusions)
        v = ""
        while i > 0:
            i, idx = divmod(i, numberBase)
            v = _indexToCharID(idx, exclusions=exclusions) + v
    else:
        v = "0"

    if pad is not None:
        v = v.zfill(pad)
    
    return v


def maxIndex(idLength: int, exclusions: List[str] = None) -> int:
    """The largest ID representable in the given number of characters

    :param idLength: The number of characters to allow in the ID
    :type idLength: int
    :param exclusions: A list of characters to exclude from the alphabet, defaults to None
    :type exclusions: List[str], optional
    :return: The largest ID representable, given `exclusions`
    :rtype: int
    """
    maxI = max(c for c in reversed(_indexToID.keys()) if exclusions is None or c not in exclusions)
    return idToIndex(_indexToID[maxI] * idLength, exclusions=exclusions)
