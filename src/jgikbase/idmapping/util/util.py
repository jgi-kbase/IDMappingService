"""

Utility functions

@author: gaprice@lbl.gov
"""
from typing import Dict as _Dict  # @UnusedImport PyDev thinks it's unused, flake & mypy get it
from typing import Pattern as _Pattern  # @UnusedImport PyDev sez it's unused, flake & mypy get it
import re as _re


def not_none(obj: object, name: str):
    """
    Check if an object is not None. In the case of a string, the string must also contain
    non-whitespace characters.

    If the object is None or a string is whitespace-only, a ValueError will be thrown.

    :param obj: the object to check
    :param name: the name of the object to use in error messages.
    """
    if not obj:
        raise ValueError(name + ' cannot be None')

# TODO EXCEP change exceptions to package specific


_REGEX_CACHE: _Dict[str, _Pattern] = {}


def check_string(string: str, name: str, legal_characters: str=None, max_len: int=None):
    '''
    Check that a string meets a set of criteria:
    - it is not None or whitespace only
    - (optional) it is less than some specified maximum length
    - (optional) it contains only legal characters.

    :param string: the string to test.
    :param name: the name of the string to be used in error messages.
    :param legal_characters: a regex character class that matches legal characters in the string.
        Typical examples are a-zA-Z0-9_, a-z, etc.
    :param max_len: the maximum length of the string.
    '''
    not_none(string, name)
    if not string.strip():
        raise ValueError(name + ' cannot be whitespace only')
    if max_len and len(string) > max_len:
        raise ValueError('{} {} exceeds maximum length of {}'
                         .format(name, string, max_len))
    if legal_characters:
        global _REGEX_CACHE
        if legal_characters not in _REGEX_CACHE:
            _REGEX_CACHE[legal_characters] = _re.compile('[^' + legal_characters + ']')
        match = _REGEX_CACHE[legal_characters].search(string)
        if match:
            raise ValueError('Illegal character in {} {}: {}'
                             .format(name, string, match.group()))
