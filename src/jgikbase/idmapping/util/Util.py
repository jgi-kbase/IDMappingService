"""

Utility functions

@author: gaprice@lbl.gov
"""
from typing import cast

# TODO docstrings should use """


def not_none(obj: object, name: str):
    """
    Check if an object is not None. In the case of a string, the string must also contain
    non-whitespace characters.

    If the object is None or a string is whitespace-only, a ValueError will be thrown.

    :param obj: the object to check
    :param name: the name of the object to use in error messages.
    """
    if type(obj) == str:
        if not cast(str, obj).strip():
            raise ValueError(name + ' cannot be None or whitespace only')
    elif not obj:
        raise ValueError(name + ' cannot be None')
