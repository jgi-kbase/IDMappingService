"""

@author: gaprice@lbl.gov
"""
from jgikbase.idmapping.storage.id_mapping_storage import IDMappingStorage as _IDMappingStorage
from jgikbase.idmapping.core.namespace_id import NamespaceID

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
