"""

@author: gaprice@lbl.gov
"""
from jgikbase.idmapping.storage.IDMappingStorage import IDMappingStorage as _IDMappingStorage
from jgikbase.idmapping.core.NamespaceID import NamespaceID

# TODO NOW


class IDMappingMongoStorage(_IDMappingStorage):
    """
    classdocs
    """

    def __init__(self):
        """
        Constructor
        """

    def create_namespace(self, namespace_id: NamespaceID) -> None:
        print('foo')
