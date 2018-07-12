'''

@author: crusherofheads
'''
from jgikbase.idmapping.storage.IDMappingStorage import IDMappingStorage as _IDMappingStorage
from jgikbase.idmapping.core.NamespaceID import NamespaceID as _NamespaceID
from jgikbase.idmapping.core.User import User as _User

# TODO NOW


class IDMappingMongoStorage(_IDMappingStorage):
    '''
    classdocs
    '''

    def __init__(self):
        '''
        Constructor
        '''

    def create_namespace(
            self,
            namespace_id: _NamespaceID,
            admin_user: _User) -> None:
        print('foo')
