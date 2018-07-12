'''
Interface for a storage system for ID mappings.

'''
from abc import abstractmethod as _abstractmethod
from abc import ABCMeta as _ABCMeta
from jgikbase.idmapping.core.NamespaceID import NamespaceID as _NamespaceID
from jgikbase.idmapping.core.User import User as _User
from jgikbase.idmapping.core.HashedToken import HashedToken as _HashedToken


class IDMappingStorage(object):
    '''
    An interface for a storage system for ID mappings. All methods are abstract.
    '''
    __metaclass__ = _ABCMeta

    @_abstractmethod
    def create_or_update_local_user(self, user: _User, token: _HashedToken) -> None:
        '''
        Create or update a user. If the user already exists, the user's token is updated.
        Once created, users cannot be removed.
        :param user: the user, which must be in the 'local' user scope.
        :param token: the user's token after applying a hash function.
        '''
        raise NotImplementedError()

    @_abstractmethod
    def create_namespace(self, namespace_id: _NamespaceID, admin_user: _User) -> None:
        '''
        Create a new namespace. Once created, namespaces cannot be removed.
        :param namespace_id: The namespace to create.
        :param admin_user: A user that will be the namespace's first administrator.

        Throws a :class:`jgikbase.idmapping.storage.Exceptions.NamespaceExistsException` if the
        namespace already exists.
        '''
        raise NotImplementedError()

    @_abstractmethod
    def add_user_to_namespace(self, namespace_id: _NamespaceID, admin_user: _User) -> None:
        '''
        Add a user to a namespace, giving them administration rights. A noop occurs if the user
        is already an administrator for the namespace.
        :param namespace_id: the namespace to modify.
        :param admin_user: the user.
        '''
        raise NotImplementedError()

    @_abstractmethod
    def remove_user_from_namespace(self, namespace_id: _NamespaceID, admin_user: _User) -> None:
        '''
        Remove a user from a namespace, removing their administration rights.
        :param namespace_id: the namespace to modify.
        :param admin_user: the user.
        '''
        raise NotImplementedError()

# TODO Add & remove mapping
# TODO find mappings from either direction
# TODO set namespace as publically mappable or not
# TODO list all users
# TODO list all users for a namespace
# TODO list all namespaces
# TODO get a namespace
