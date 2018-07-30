"""
The core ID mapping code.
"""
from jgikbase.idmapping.storage.id_mapping_storage import IDMappingStorage
from jgikbase.idmapping.core.user_handler import UserHandler
from typing import Set
from jgikbase.idmapping.core.util import not_none, no_Nones_in_iterable
from jgikbase.idmapping.core.object_id import NamespaceID
from jgikbase.idmapping.core.user import User, AuthsourceID
from jgikbase.idmapping.core.errors import NoSuchAuthsourceError, NoSuchUserError, \
     UnauthorizedError
from jgikbase.idmapping.core.tokens import Token

# TODO NOW logging
# TODO NOW implement rest of methods necessary for API


class IDMapper:
    """
    The core ID Mapping class. Allows for creating namespaces, administrating namespaces, and
    creating and deleting mappings, as well as listing namespaces and mappings.
    """

    def __init__(
            self,
            user_handlers: Set[UserHandler],
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
        no_Nones_in_iterable(user_handlers, 'user_handlers')
        no_Nones_in_iterable(admin_authsources, 'admin_authsources')
        not_none(storage, 'storage')
        self._storage = storage
        self._handlers = {handler.get_authsource_id(): handler for handler in user_handlers}
        self._admin_authsources = admin_authsources

    def _check_authsource_id(self, authsource_id):
        """
        :raises NoSuchAuthsourceError: if there's no handler for the provided authsource.
        """
        not_none(authsource_id, 'authsource_id')
        if authsource_id not in self._handlers:
            raise NoSuchAuthsourceError(authsource_id.id)

    def _check_sys_admin(self, authsource_id: AuthsourceID, token: Token) -> None:
        """
        :raises NoSuchAuthsourceError: if there's no handler for the provided authsource.
        :raises InvalidTokenError: if the token is invalid.
        :raises UnauthorizedError: if the user is not a system administrator.
        """
        not_none(token, 'token')
        self._check_authsource_id(authsource_id)
        if authsource_id not in self._admin_authsources:
            raise UnauthorizedError(('Auth source {} is not configured as a provider of ' +
                                    'system administration status').format(authsource_id.id))
        # TODO CACHE cache get_user results
        user, admin = self._handlers[authsource_id].get_user(token)
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
        self._check_authsource_id(user.authsource_id)
        # TODO CACHE cache is valid user results
        if not self._handlers[user.authsource_id].is_valid_user(user.username):
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
        :raises NoSuchAuthsourceError: if there's no handler for the provided authsource ID or the
            user's authsource.
        :raises NoSuchNamespaceError: if the namespace does not exist.
        :raises NoSuchUserError: if the user is invalid according to the appropriate user handler
           or the user does not administrate the namespace.
        :raises InvalidTokenError: if the token is invalid.
        :raises UnauthorizedError: if the user is not a system administrator.
        """
        not_none(namespace_id, 'namespace_id')
        not_none(user, 'user')
        self._check_sys_admin(authsource_id, token)
        self._check_valid_user(user)
        self._storage.remove_user_from_namespace(namespace_id, user)

    def _check_authed_for_ns(self, user: User, nsid: NamespaceID) -> None:
        """
        :raises UnauthorizedError: if the user is not authorized to administrate the namespace.
        :raises NoSuchNamespaceError: if the namespace does not exist.
        """
        ns = self._storage.get_namespace(nsid)
        if user not in ns.authed_users:
            raise UnauthorizedError('User {}/{} may not administrate namespace {}'.format(
                user.authsource_id.id, user.username.name, nsid.id))

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
        self._check_authsource_id(authsource_id)
        # TODO CACHE cache get_user results
        user, _ = self._handlers[authsource_id].get_user(token)
        self._check_authed_for_ns(user, namespace_id)
        self._storage.set_namespace_publicly_mappable(namespace_id, publicly_mappable)
