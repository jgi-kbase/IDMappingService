"""
Interface for a storage system for ID mappings.

"""
# it'd be nice if you could just pragma: no cover the entire file, but that doesn't seem to work
from abc import abstractmethod as _abstractmethod  # pragma: no cover
from abc import ABCMeta as _ABCMeta  # pragma: no cover
from jgikbase.idmapping.core.object_id import NamespaceID  # pragma: no cover
from jgikbase.idmapping.core.user import User  # pragma: no cover
from jgikbase.idmapping.core.tokens import HashedToken  # pragma: no cover
from jgikbase.idmapping.core.object_id import Namespace  # pragma: no cover
from typing import Iterable, Set, Tuple  # pragma: no cover
from jgikbase.idmapping.core.object_id import ObjectID  # pragma: no cover


class IDMappingStorage:  # pragma: no cover
    """
    An interface for a storage system for ID mappings. All methods are abstract.
    """
    __metaclass__ = _ABCMeta

    @_abstractmethod
    def create_local_user(self, user: User, token: HashedToken) -> None:
        """
        Create a user.
        Once created, users cannot be removed. The client programmer is responsible for
        ensuring that the token provided does not already exist in the database.

        :param user: the user, which must be in the 'local' user scope.
        :param token: the user's token after applying a hash function.
        :raises ValueError: if the token already exists in the database or the user is not a
            local user (e.g. uses the :const:`jgikbase.idmapping.core.user.LOCAL` authsource).
        :raises TypeError: if any of the arguments are None.
        :raises UserExistsError: if the user already exists.
        :raises IDMappingStorageError: if an unexpected error occurs.
        """
        raise NotImplementedError()

    @_abstractmethod
    def update_local_user(self, user: User, token: HashedToken) -> None:
        """
        Update an existing user's token.

        :param user: the user, which must be in the 'local' user scope.
        :param token: the user's token after applying a hash function.
        :raises ValueError: if the token already exists in the database or the user is not a
            local user (e.g. uses the :const:`jgikbase.idmapping.core.user.LOCAL` authsource).
        :raises TypeError: if any of the arguments are None.
        :raises NoSuchUserError: if the user does not exist.
        :raises IDMappingStorageError: if an unexpected error occurs.
        """
        raise NotImplementedError()

    @_abstractmethod
    def get_user(self, token: HashedToken) -> User:
        """
        Get the user, if any, associated with a hashed token.

        :param token: the hashed token.
        :raises TypeError: if the token is None.
        :raises InvalidTokenError: if the token does not exist in the storage system.
        :raises IDMappingStorageError: if an unexpected error occurs.
        """
        raise NotImplementedError()

    @_abstractmethod
    def get_users(self) -> Set[User]:
        """
        Get all the users in the system.

        :raises IDMappingStorageError: if an unexpected error occurs.
        """
        raise NotImplementedError()

    @_abstractmethod
    def create_namespace(self, namespace_id: NamespaceID) -> None:
        """
        Create a new namespace. Once created, namespaces cannot be removed.

        :param namespace_id: The namespace to create.
        :raises TypeError: if the namespace ID is None.
        :raises NamespaceExistsError: if the namespace already exists.
        """
        raise NotImplementedError()

    @_abstractmethod
    def add_user_to_namespace(self, namespace_id: NamespaceID, admin_user: User) -> None:
        """
        Add a user to a namespace, giving them administration rights. A noop occurs if the user
        is already an administrator for the namespace.

        :param namespace_id: the namespace to modify.
        :param admin_user: the user.
        :raises TypeError: if any of the arguments are None.
        :raises NoSuchNamespaceError: if the namespace does not exist.
        :raises UserExistsError: if the user already administrates the namespace.
        """
        raise NotImplementedError()

    @_abstractmethod
    def remove_user_from_namespace(self, namespace_id: NamespaceID, admin_user: User) -> None:
        """
        Remove a user from a namespace, removing their administration rights.

        :param namespace_id: the namespace to modify.
        :param admin_user: the user.
        :raises TypeError: if any of the arguments are None.
        :raises NoSuchNamespaceError: if the namespace does not exist.
        :raises NoSuchUserError: if the user does not administrate the namespace.
        """
        raise NotImplementedError()

    @_abstractmethod
    def set_namespace_publicly_mappable(self, namespace_id: NamespaceID, publically_mappable: bool
                                        ) -> None:
        """
        Set the publicly mappable flag on a namespace.

        :param namespace_id: The namespace to alter.
        :param publically_mappable: True to set the namespace to publicly mappable, False or None
            to prevent public mapping.
        :raises TypeError: if namespace_id is None.
        :raises NoSuchNamespaceError: if the namespace does not exist.
        """
        raise NotImplementedError()

    @_abstractmethod
    def get_namespaces(self) -> Set[Namespace]:
        """
        Get all the namespaces in the system.
        """
        raise NotImplementedError()

    @_abstractmethod
    def get_namespace(self, namespace_id: NamespaceID) -> Namespace:
        """
        Get a particular namespace.

        :param namespace_id: the id of the namespace to get.
        :raises TypeError: if the namespace ID is None.
        :raises NoSuchNamespaceError: if the namespace does not exist.
        """
        raise NotImplementedError()

    @_abstractmethod
    def add_mapping(self, primary_OID: ObjectID, secondary_OID: ObjectID) -> None:
        """
        Create a mapping from one namespace to another.
        Note that this method does NOT check for the existence of the namespaces.
        If the mapping already exists, no further action is taken.

        :param primary_OID: the primary namespace/ID combination.
        :param secondary_OID: the secondary namespace/ID combination.
        :raise TypeError: if any of the arguments are None.
        :raise ValueError: if the namespace IDs are the same.
        """
        raise NotImplementedError()

    @_abstractmethod
    def remove_mapping(self, primary_OID: ObjectID, secondary_OID: ObjectID) -> bool:
        """
        Remove a mapping from one namespace to another. Returns true if a mapping was removed,
        false otherwise.

        :param primary_OID: the primary namespace/ID combination.
        :param secondary_OID: the secondary namespace/ID combination.
        :raise TypeError: if any of the arguments are None.
        """
        raise NotImplementedError()

    @_abstractmethod
    def find_mappings(self, oid: ObjectID, ns_filter: Iterable[NamespaceID]=None
                      ) -> Tuple[Set[ObjectID], Set[ObjectID]]:
        """
        Find mappings given a namespace / id combination. The first set of object IDs in the
        returned tuple are mappings where the provided object ID is the primary object ID, and
        the second set in the tuple are mappings where the provided object ID is the
        secondary object ID.
        If the namespace or id does not exist, no results will be returned. The namespaces in the
        filter are ignored if they do not exist.

        :param oid: the namespace / id combination to match against.
        :param ns_filter: a list of namespaces with which to filter the results. Only results in
            these namespaces will be returned.
        :raise TypeError: if the object ID is None or the filter contains None.
        """
        raise NotImplementedError()
