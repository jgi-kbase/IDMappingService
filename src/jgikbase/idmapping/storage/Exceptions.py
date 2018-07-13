"""
Exception classes thrown by the storage system.

@author: gaprice@lbl.gov
"""


class NamespaceExistsException(Exception):
    """
    Exception thrown when attempting to create a namespace that already exists.
    """
