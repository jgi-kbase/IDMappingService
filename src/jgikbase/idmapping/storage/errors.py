"""
Exceptions for storage events.
"""


class IDMappingStorageError(Exception):
    """
    Superclass of all storage related exceptions. Denotes a general storage error.
    """


class StorageInitException(Exception):
    """
    Denotes an error during initialization of the storage system.
    """
