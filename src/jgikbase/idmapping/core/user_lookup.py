from abc import ABCMeta as _ABCMeta, abstractmethod as _abstractmethod
from jgikbase.idmapping.core.tokens import Token
from jgikbase.idmapping.core.user import User, AuthsourceID, Username
from jgikbase.idmapping.storage.id_mapping_storage import IDMappingStorage
from jgikbase.idmapping.core.arg_check import not_none, no_Nones_in_iterable
from jgikbase.idmapping.core import tokens
from typing import Dict, Tuple, Optional, Set, Callable
from jgikbase.idmapping.core.errors import NoSuchAuthsourceError
import time
from cacheout.lru import LRUCache


class UserLookup:  # pragma: no cover
    """
    An interface for a handler for user information, including authentication.
    """

    __metaclass__ = _ABCMeta

    @_abstractmethod
    def get_authsource_id(self) -> AuthsourceID:
        """
        Get the ID of the authentication source that this handler handles.
        """
        raise NotImplementedError()

    @_abstractmethod
    def get_user(self, token: Token) -> Tuple[User, bool, Optional[int], Optional[int]]:
        """
        Get a user given a token.

        :param token: the token.
        :raises InvalidTokenError: if the token is invalid.
        :raises TypeError: if the token is None.
        :returns: a tuple of 1) the user corresponding to the token, 2) a boolean describing
            whether the handler claims they are a system admin (True) or not (False), 3)
            a unix epoch timestamp in seconds providing an absolute limit for the cache lifetime
            of this result, and 4) a relative cache expiration time in seconds. If both 3) and 4)
            are None, the process implementing the cache must make its own decisions regarding
            the cache lifetime.
        """
        raise NotImplementedError()

    @_abstractmethod
    def is_valid_user(
        self, username: Username
    ) -> Tuple[bool, Optional[int], Optional[int]]:
        """
        Check if a username is valid, which implies the user exists.

        :param username: the username to check.
        :raises TypeError: if the argument is None.
        :returns: a tuple of 1) a boolean describing whether the user exists or not, 2)
            a unix epoch timestamp in seconds providing an absolute limit for the cache lifetime
            of this result, and 3) a relative cache expiration time in seconds. If both 3) and 4)
            are None, the process implementing the cache must make its own decisions regarding
            the cache lifetime.
        """
        raise NotImplementedError()


class UserLookupSet:
    """
    A container for a number of user handlers that provides caching for said handlers.
    """

    def __init__(
        self,
        user_lookup: Set[UserLookup],
        cache_timer: Callable[[], int] = None,
        cache_max_size: int = 10000,
        cache_user_expiration: int = 300,
        cache_is_valid_expiration: int = 3600,
    ) -> None:
        """
        Create the handler set.

        The cache_* parameters are mainly provided for testing purposes.

        :param user_lookup: the set of user lookup instances to query when looking up user names
            from tokens or checking that a provided user name is valid.
        :param cache_timer: the timer used for cache expiration. Defaults to time.time.
        :param cache_max_size: the maximum size of the token -> user and username -> validity
            caches.
        :param cache_user_expiration: the default expiration time for the token -> user cache in
            seconds. This time can be overridden by a user handler on a per token basis.
        :param cache_is_valid_expiration: the default expiration time for the  username ->
            validity cache. This time can be overridden by a user handler on a per user basis.
        """
        no_Nones_in_iterable(user_lookup, "user_lookup")
        self._lookup = {lookup.get_authsource_id(): lookup for lookup in user_lookup}
        self._cache_timer = time.time if not cache_timer else cache_timer
        self._user_cache = LRUCache(
            timer=self._cache_timer, maxsize=cache_max_size, ttl=cache_user_expiration
        )
        self._valid_cache = LRUCache(
            timer=self._cache_timer,
            maxsize=cache_max_size,
            ttl=cache_is_valid_expiration,
        )

    def _check_authsource_id(self, authsource_id: AuthsourceID) -> None:
        """
        :raises NoSuchAuthsourceError: if there's no handler for the provided authsource.
        """
        not_none(authsource_id, "authsource_id")
        if authsource_id not in self._lookup:
            raise NoSuchAuthsourceError(authsource_id.id)

    def _calc_ttl(self, epoch, rel):
        if not rel and not epoch:
            return None
        if not rel:
            return epoch - self._cache_timer()
        if not epoch:
            return rel
        return min(epoch - self._cache_timer(), rel)

    def get_user(self, authsource_id: AuthsourceID, token: Token) -> Tuple[User, bool]:
        """
        Get a user given the user's token.

        :param authsource_id: the authsource where the user resides.
        :param token: the users's token.
        :raises TypeError: if any of the arguments are None.
        :raises NoSuchAuthsourceError: if there's no handler for the provided authsource.
        :raises InvalidTokenError: if the token is invalid.
        :returns: a tuple of the user and a boolean indicating whether the authsource claims
            the user is a mapping service system admin.
        """
        not_none(token, "token")
        self._check_authsource_id(authsource_id)
        # None default causes a key error
        cacheres = self._user_cache.get((authsource_id, token), default=False)
        if cacheres:
            return cacheres
        user, admin, epoch, rel = self._lookup[authsource_id].get_user(token)
        self._user_cache.set(
            (authsource_id, token), (user, admin), ttl=self._calc_ttl(epoch, rel)
        )
        return (user, admin)

    def is_valid_user(self, user: User) -> bool:
        """
        Check whether a given user exists.

        :param user: the user to check.
        :raises NoSuchAuthsourceError: if there's no handler for the user's authsource.
        """
        not_none(user, "user")
        self._check_authsource_id(user.authsource_id)
        # None default causes a key error
        exists = self._valid_cache.get(user, default=False)
        if not exists:
            exists, epoch, rel = self._lookup[user.authsource_id].is_valid_user(
                user.username
            )
            if exists:
                self._valid_cache.set(user, True, ttl=self._calc_ttl(epoch, rel))
        return exists


class LocalUserLookup(UserLookup):
    """
    An implementation of :class:`jgikbase.idmapping.core.user_handler.UserLookup` for users
    stored in the local database.
    """

    LOCAL = AuthsourceID("local")
    """ The ID of the authentication source for local users. """

    def __init__(self, storage: IDMappingStorage) -> None:
        """
        Create a local user handler.

        :param storage: the storage system in which users are stored.
        """
        not_none(storage, "storage")
        self._store = storage

    def get_authsource_id(self) -> AuthsourceID:
        return self.LOCAL

    def get_user(self, token: Token) -> Tuple[User, bool, Optional[int], Optional[int]]:
        not_none(token, "token")
        username, admin = self._store.get_user(token.get_hashed_token())
        return (User(self.LOCAL, username), admin, None, 300)

    def is_valid_user(
        self, username: Username
    ) -> Tuple[bool, Optional[int], Optional[int]]:
        not_none(username, "username")
        return (self._store.user_exists(username), None, 3600)

    def create_user(self, username: Username) -> Token:
        """
        Create a new user in the local storage system. Returns a new token for that user.

        :param username: The name of the user to create.
        :raises TypeError: if the user name is None.
        :raises UserExistsError: if the user already exists.
        """
        not_none(username, "username")
        t = tokens.generate_token()
        self._store.create_local_user(username, t.get_hashed_token())
        return t

    def new_token(self, username: Username) -> Token:
        """
        Generate a new token for a user in the local storage system.

        :param username: The name of the user to update.
        :raises TypeError: if the user name is None.
        :raises NoSuchUserError: if the user does not exist.
        """
        not_none(username, "username")
        t = tokens.generate_token()
        self._store.update_local_user_token(username, t.get_hashed_token())
        return t

    def set_user_as_admin(self, username: Username, admin: bool) -> None:
        """
        Set or remove a local user's administration status.

        :param username: the name of the user to alter.
        :param admin: True to give the user admin privileges, False to remove them. If the user
            is already in the given state, no further action is taken.
        :raises TypeError: if the username is None.
        """
        not_none(username, "username")
        self._store.set_local_user_as_admin(username, admin)

    def get_users(self) -> Dict[Username, bool]:
        """
        Get the users in the local storage system.

        :returns: a mapping of username to a boolean denoting whether the user is an admin or not.
        """
        return self._store.get_users()


class LookupInitializationError(Exception):
    """Thrown when a user lookup handler could not be initialized."""
