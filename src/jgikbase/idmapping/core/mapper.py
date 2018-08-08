"""
The core ID mapping code.
"""
from jgikbase.idmapping.storage.id_mapping_storage import IDMappingStorage
from jgikbase.idmapping.core.user_lookup import UserHandlerSet
from typing import Set, cast, Tuple, Iterable
from jgikbase.idmapping.core.arg_check import not_none, no_Nones_in_iterable
from jgikbase.idmapping.core.object_id import NamespaceID, Namespace, ObjectID
from jgikbase.idmapping.core.user import User, AuthsourceID
from jgikbase.idmapping.core.errors import NoSuchUserError, UnauthorizedError
from jgikbase.idmapping.core.tokens import Token

# TODO NOW logging


class IDMapper:
    """
    The core ID Mapping class. Allows for creating namespaces, administrating namespaces, and
    creating and deleting mappings, as well as listing namespaces and mappings.
    """

    def __init__(
            self,
            user_handlers: UserHandlerSet,
            admin_authsources: Set[AuthsourceID],
            storage: IDMappingStorage
            ) -> None:
        """
        Create the mapper.

        :param user_handlers: the set of user handlers to query when looking up user names from
            tokens or checking that a provided user name is valid.
        :param admin_authsources: the set of auth sources that are valid system admin sources.
            The admin state returned by other auth sources will be ignored.
        :param storage: the mapping storage system.
        """
        not_none(user_handlers, 'user_handlers')
        no_Nones_in_iterable(admin_authsources, 'admin_authsources')
        not_none(storage, 'storage')
        self._storage = storage
        self._handlers = user_handlers
        self._admin_authsources = admin_authsources

    def _check_sys_admin(self, authsource_id: AuthsourceID, token: Token) -> None:
        """
        :raises NoSuchAuthsourceError: if there's no handler for the provided authsource.
        :raises InvalidTokenError: if the token is invalid.
        :raises UnauthorizedError: if the user is not a system administrator.
        """
        not_none(token, 'token')
        if authsource_id not in self._admin_authsources:
            raise UnauthorizedError(('Auth source {} is not configured as a provider of ' +
                                    'system administration status').format(authsource_id.id))
        user, admin = self._handlers.get_user(authsource_id, token)
        if not admin:
            raise UnauthorizedError('User {}/{} is not a system administrator'.format(
                user.authsource_id.id, user.username.name))

    def create_namespace(
            self,
            authsource_id: AuthsourceID,
            token: Token,
            namespace_id: NamespaceID
            ) -> None:
        """
        Create a namespace.

        :param authsource_id: The authentication source to be used to look up the user token.
        :param token: the user's token.
        :param namespace_id: The namespace to create.
        :raises TypeError: if any of the arguments are None.
        :raises NoSuchAuthsourceError: if there's no handler for the provided authsource.
        :raises NamespaceExistsError: if the namespace already exists.
        :raises InvalidTokenError: if the token is invalid.
        :raises UnauthorizedError: if the user is not a system administrator.
        """
        not_none(namespace_id, 'namespace_id')
        self._check_sys_admin(authsource_id, token)
        self._storage.create_namespace(namespace_id)

    def _check_valid_user(self, user):
        """
        :raises NoSuchAuthsourceError: if there's no handler for the user's authsource.
        :raises NoSuchUserError: if the user is invalid according to the appropriate user handler.
        """
        not_none(user, 'user')
        if not self._handlers.is_valid_user(user):
            raise NoSuchUserError('{}/{}'.format(user.authsource_id.id, user.username.name))

    def add_user_to_namespace(
            self,
            authsource_id: AuthsourceID,
            token: Token,
            namespace_id: NamespaceID,
            user: User
            ) -> None:
        """
        Add a user to a namespace.

        :param authsource_id: The authentication source to be used to look up the user token.
        :param token: the user's token.
        :param namespace_id: the namespace to modify.
        :param user: the user.
        :raises TypeError: if any of the arguments are None.
        :raises NoSuchAuthsourceError: if there's no handler for the provided authsource ID or the
            user's authsource.
        :raises NoSuchNamespaceError: if the namespace does not exist.
        :raises NoSuchUserError: if the user is invalid according to the appropriate user handler.
        :raises UserExistsError: if the user already administrates the namespace.
        :raises InvalidTokenError: if the token is invalid.
        :raises UnauthorizedError: if the user is not a system administrator.
        """
        not_none(namespace_id, 'namespace_id')
        not_none(user, 'user')
        self._check_sys_admin(authsource_id, token)
        self._check_valid_user(user)
        self._storage.add_user_to_namespace(namespace_id, user)

    def remove_user_from_namespace(
            self,
            authsource_id: AuthsourceID,
            token: Token,
            namespace_id: NamespaceID,
            user: User
            ) -> None:
        """
        Remove a user from a namespace.

        :param authsource_id: The authentication source to be used to look up the user token.
        :param token: the user's token.
        :param namespace_id: the namespace to modify.
        :param user: the user.
        :raises TypeError: if any of the arguments are None.
        :raises NoSuchAuthsourceError: if there's no handler for the provided authsource ID.
        :raises NoSuchNamespaceError: if the namespace does not exist.
        :raises NoSuchUserError: if the user does not administrate the namespace.
        :raises InvalidTokenError: if the token is invalid.
        :raises UnauthorizedError: if the user is not a system administrator.
        """
        not_none(namespace_id, 'namespace_id')
        not_none(user, 'user')
        self._check_sys_admin(authsource_id, token)
        self._storage.remove_user_from_namespace(namespace_id, user)

    def _check_authed_for_ns_get(self, user: User, namespace_id: NamespaceID) -> None:
        """
        :raises UnauthorizedError: if the user is not authorized to administrate the namespace.
        :raises NoSuchNamespaceError: if the namespace does not exist.
        """
        self._check_authed_for_ns(user, self._storage.get_namespace(namespace_id))

    def _check_authed_for_ns(self, user: User, ns: Namespace) -> None:
        """
        :raises UnauthorizedError: if the user is not authorized to administrate the namespace.
        """
        if user not in ns.authed_users:
            raise UnauthorizedError('User {}/{} may not administrate namespace {}'.format(
                user.authsource_id.id, user.username.name, ns.namespace_id.id))

    def set_namespace_publicly_mappable(
            self,
            authsource_id: AuthsourceID,
            token: Token,
            namespace_id: NamespaceID,
            publicly_mappable: bool
            ) -> None:
        """
        Set a namespace to be publicly mappable, or remove that state. A publicly mappable
        namespace may have ID mappings added to it without the user being an administrator
        of the namespace. The user must always be an administrator of the primary ID of the ID
        tuple.

        :param authsource_id: The authentication source to be used to look up the user token.
        :param token: the user's token.
        :param namespace_id: the ID of the namespace to modify.
        :param publicly_mappable: True to set the namespace to publicly mappable, false otherwise.
        :raises TypeError: if authsource ID, namespace ID, or token are None.
        :raises NoSuchAuthsourceError: if there's no handler for the provided authsource.
        :raises InvalidTokenError: if the token is invalid.
        :raises NoSuchNamespaceError: if the namespace does not exist.
        :raises UnauthorizedError: if the user is not authorized to administrate the namespace.
        """
        not_none(token, 'token')
        not_none(namespace_id, 'namespace_id')
        user, _ = self._handlers.get_user(authsource_id, token)
        self._check_authed_for_ns_get(user, namespace_id)
        self._storage.set_namespace_publicly_mappable(namespace_id, publicly_mappable)

    def get_namespace(
            self,
            namespace_id: NamespaceID,
            authsource_id: AuthsourceID=None,
            token: Token=None
            ) -> Namespace:
        """
        Get a namespace. If user credentials are provided and the user is a system admin or an
        admin of the namespace, the namespace user list will be returned. Otherwise, the user
        list will be empty.

        :param namespace_id: the ID of the namepspace to get.
        :param authsource_id: the authsource of the provided token.
        :param token: the user's token.
        :raises TypeError: if the namespace ID is None or only one of the authsource ID or token
            are supplied.
        :raises NoSuchNamespaceError: if the namespace does not exist.
        :raises NoSuchAuthsourceError: if there's no handler for the provided authsource.
        :raises InvalidTokenError: if the token is invalid.
        """
        not_none(namespace_id, 'namespace_id')
        if bool(authsource_id) ^ bool(token):  # xor
            raise TypeError('If token or authsource_id is specified, both must be specified')
        ns = self._storage.get_namespace(namespace_id)
        if token:
            authsource_id = cast(AuthsourceID, authsource_id)  # mypy doesn't understand the xor
            user, admin = self._handlers.get_user(authsource_id, token)
            if admin or user in ns.authed_users:
                return ns
        return ns.without_users()

    def get_namespaces(self) -> Tuple[Set[NamespaceID], Set[NamespaceID]]:
        """
        Get all the namespaces in the system.

        :returns: A 2-tuple of sets of namespace IDs. The first set is publicly mappable, the
            second set is not.
        """
        # could make a more efficient storage method if this proves to be slow
        # since we're pulling back user data we don't need
        nss = self._storage.get_namespaces()
        public = set()
        private = set()
        for ns in nss:
            if ns.is_publicly_mappable:
                public.add(ns.namespace_id)
            else:
                private.add(ns.namespace_id)
        return public, private

    def create_mapping(
            self,
            authsource_id: AuthsourceID,
            token: Token,
            administrative_oid: ObjectID,
            oid: ObjectID
            ) -> None:
        """
        Create a mapping. The user must be an administrator of the namespace in the
        administrative_oid and an administrator of the namespace in the oid if it is not
        publicly mappable.

        :param authsource_id: the authsource of the provided token.
        :param token: the user's token.
        :param administrative_oid: the administrative object ID.
        :param oid: the other object ID.

        :raises TypeError: if any of the arguments are None,
        :raises NoSuchAuthsourceError: if there's no handler for the provided authsource.
        :raises InvalidTokenError: if the token is invalid.
        :raises NoSuchNamespaceError: if either of the namespaces do not exist.
        :raises UnauthorizedError: if the user is not authorized to administrate either of
            the namespaces.
        """
        not_none(token, 'token')
        not_none(administrative_oid, 'administrative_oid')
        not_none(oid, 'oid')
        user, _ = self._handlers.get_user(authsource_id, token)
        adminns = self._storage.get_namespace(administrative_oid.namespace_id)
        self._check_authed_for_ns(user, adminns)
        ns = self._storage.get_namespace(oid.namespace_id)
        if not ns.is_publicly_mappable:
            self._check_authed_for_ns(user, ns)
        self._storage.add_mapping(administrative_oid, oid)

    def remove_mapping(
            self,
            authsource_id: AuthsourceID,
            token: Token,
            administrative_oid: ObjectID,
            oid: ObjectID
            ) -> None:
        """
        Delete a mapping. The user must be an administrator of the namespace in the
        administrative_oid.

        :param authsource_id: the authsource of the provided token.
        :param token: the user's token.
        :param administrative_oid: the administrative object ID.
        :param oid: the other object ID.

        :raises TypeError: if any of the arguments are None,
        :raises NoSuchAuthsourceError: if there's no handler for the provided authsource.
        :raises InvalidTokenError: if the token is invalid.
        :raises NoSuchNamespaceError: if either of the namespaces do not exist.
        :raises UnauthorizedError: if the user is not authorized to administrate the
            administrative namespace.
        """
        not_none(token, 'token')
        not_none(administrative_oid, 'administrative_oid')
        not_none(oid, 'oid')
        user, _ = self._handlers.get_user(authsource_id, token)
        adminns = self._storage.get_namespace(administrative_oid.namespace_id)
        self._check_authed_for_ns(user, adminns)
        self._storage.get_namespace(oid.namespace_id)  # check for existence
        self._storage.remove_mapping(administrative_oid, oid)

    def get_mappings(self, oid: ObjectID, ns_filter: Iterable[NamespaceID]=None
                     ) -> Tuple[Set[ObjectID], Set[ObjectID]]:
        """
        Find mappings given a namespace / id combination.

        If the id does not exist, no results will be returned.

        :param oid: the namespace / id combination to match against.
        :param ns_filter: a list of namespaces with which to filter the results. Only results in
            these namespaces will be returned.
        :returns: a tuple of sets of object IDs. The first set in the tuple contains mappings
            where the provided object ID is the administrative object ID, and the second set
            contains the remainder of the mappings.
        :raise TypeError: if the object ID is None or the filter contains None.
        :raise NoSuchNamespaceError: if any of the namespaces do not exist.
        """
        not_none(oid, 'oid')
        check = [oid.namespace_id]
        if ns_filter:
            no_Nones_in_iterable(ns_filter, 'ns_filter')
            check.extend(ns_filter)
        # check for existence
        self._storage.get_namespaces(check)  # check for existence
        return self._storage.find_mappings(oid, ns_filter=ns_filter)
