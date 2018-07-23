"""

Utility functions

"""
from typing import Dict as _Dict  # @UnusedImport PyDev thinks it's unused, flake & mypy get it
from typing import Pattern as _Pattern  # @UnusedImport PyDev sez it's unused, flake & mypy get it
import re as _re
from jgikbase.idmapping.core.errors import MissingParameterError, IllegalParameterError


def not_none(obj: object, name: str):
    """
    Check if an object is not None.

    :param obj: the object to check
    :param name: the name of the object to use in error messages.
    :raises MissingParameterError: if the object is None.
    """
    if not obj:
        raise MissingParameterError(name)


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
        Typical examples are a-zA-Z_0-9, a-z, etc.
    :param max_len: the maximum length of the string.
    :raises MissingParameterError: if the string is None or whitespace only.
    :raises IllegalParameterError: if the string is too long or contains illegal characters.
    '''
    not_none(string, name)
    if not string.strip():
        raise MissingParameterError(name)
    if max_len and len(string) > max_len:
        raise IllegalParameterError('{} {} exceeds maximum length of {}'
                                    .format(name, string, max_len))
    if legal_characters:
        global _REGEX_CACHE
        if legal_characters not in _REGEX_CACHE:
            _REGEX_CACHE[legal_characters] = _re.compile('[^' + legal_characters + ']')
        match = _REGEX_CACHE[legal_characters].search(string)
        if match:
            raise IllegalParameterError('Illegal character in {} {}: {}'
                                        .format(name, string, match.group()))
