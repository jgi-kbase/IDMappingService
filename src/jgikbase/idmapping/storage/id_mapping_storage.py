"""
Interface for a storage system for ID mappings.

"""
from abc import abstractmethod as _abstractmethod
from abc import ABCMeta as _ABCMeta
from jgikbase.idmapping.core.namespace_id import NamespaceID
from jgikbase.idmapping.core.user import User
from jgikbase.idmapping.core.tokens import HashedToken
from jgikbase.idmapping.core.namespace import Namespace
from typing import List
from jgikbase.idmapping.core.namespaced_id import NamespacedID

# TODO make the coverage calculation not care about abstract classes


class IDMappingStorage:
    """
    An interface for a storage system for ID mappings. All methods are abstract.
    """
    __metaclass__ = _ABCMeta

    @_abstractmethod
    def create_or_update_local_user(self, user: User, token: HashedToken) -> None:
        """
        Create or update a user. If the user already exists, the user's token is updated.
        Once created, users cannot be removed.

        :param user: the user, which must be in the 'local' user scope.
        :param token: the user's token after applying a hash function.
        """
        raise NotImplementedError()

    @_abstractmethod
    def get_users(self) -> List[User]:
        """
        Get all the users in the system.
        """
        raise NotImplementedError()

    @_abstractmethod
    def create_namespace(self, namespace_id: NamespaceID) -> None:
        """
        Create a new namespace. Once created, namespaces cannot be removed.

        :param namespace_id: The namespace to create.

        Throws a :class:`jgikbase.idmapping.storage.exceptions.NamespaceExistsException` if the
        namespace already exists.
        """
        raise NotImplementedError()

    @_abstractmethod
    def add_user_to_namespace(self, namespace_id: NamespaceID, admin_user: User) -> None:
        """
        Add a user to a namespace, giving them administration rights. A noop occurs if the user
        is already an administrator for the namespace.

        :param namespace_id: the namespace to modify.
        :param admin_user: the user.
        """
        # TODO throw no such namespace
        raise NotImplementedError()

    @_abstractmethod
    def remove_user_from_namespace(self, namespace_id: NamespaceID, admin_user: User) -> None:
        """
        Remove a user from a namespace, removing their administration rights.

        :param namespace_id: the namespace to modify.
        :param admin_user: the user.
        """
        # TODO throw no such namespace
        raise NotImplementedError()

    @_abstractmethod
    def get_users_for_namespace(self, namespace_id: NamespaceID) -> List[User]:
        """
        Get the users that can administrate a particular namespace.

        :param namespace_id: The namespace to query.
        """
        # TODO throw no such namespace
        raise NotImplementedError()

    @_abstractmethod
    def set_namespace_publicly_mappable(
            self,
            namespace_id: NamespaceID,
            publically_mappable: bool=False
            ) -> None:
        """
        Set the publicly mappable flag on a namespace.

        :param namespace_id: The namespace to alter.
        :param publically_mappable: True to set the namespace to publicly mappable, False (the
            default) to prevent public mapping.
        """
        # TODO throw no such namespace
        raise NotImplementedError()

    @_abstractmethod
    def get_namespaces(self) -> List[Namespace]:
        """
        Get all the namespaces in the system.
        """
        raise NotImplementedError()

    @_abstractmethod
    def get_namespace(self, namespace_id: NamespaceID) -> Namespace:
        """
        Get a particular namespace.

        :param namespace_id: the id of the namespace to get.
        """
        # TODO throw no such namespace
        raise NotImplementedError()

    @_abstractmethod
    def add_mapping(self, primary_NID: NamespacedID, secondary_NID: NamespacedID) -> None:
        """
        Create a mapping from one namespace to another.
        Note that this method does NOT check for the existence of the namespaces.

        :param primary_NID: the primary namespace/ID combination.
        :param secondary_NID: the secondary namespace/ID combination.
        """
        raise NotImplementedError()

    @_abstractmethod
    def remove_mapping(self, primary_NID: NamespacedID, secondary_NID: NamespacedID) -> None:
        """
        Remove a mapping from one namespace to another.

        :param primary_NID: the primary namespace/ID combination.
        :param secondary_NID: the secondary namespace/ID combination.
        """
        raise NotImplementedError()

    @_abstractmethod
    def find_mappings(
            self,
            nid: NamespacedID,
            ns_filter: List[NamespaceID]=None
            ) -> List[NamespacedID]:
        """
        Find mappings given a namespace / id combination.
        If the namespace does not exist, no results will be returned.

        :param nid: the namespace / id combination to match against.
        :param ns_filter: a list of namespaces with which to filter the results. Only results in
            these namespaces will be returned.
        """
        raise NotImplementedError()
