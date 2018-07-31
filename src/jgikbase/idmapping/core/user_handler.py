from abc import ABCMeta as _ABCMeta, abstractmethod as _abstractmethod
from jgikbase.idmapping.core.tokens import Token
from jgikbase.idmapping.core.user import User, AuthsourceID, Username
from jgikbase.idmapping.storage.id_mapping_storage import IDMappingStorage
from jgikbase.idmapping.core.util import not_none
from jgikbase.idmapping.core import tokens
from typing import Dict


class UserHandler:  # pragma: no cover
    """
    An interface for a handler for user information, including authentication.
    """
    __metaclass__ = _ABCMeta

    @_abstractmethod
    def get_authsource_id(self) -> AuthsourceID:
        '''
        Get the ID of the authentication source that this handler handles.
        '''
        raise NotImplementedError()

    @_abstractmethod
    def get_user(self, token: Token) -> User:
        '''
        Get a user given a token.

        :param token: the token.
        :raises InvalidTokenError: if the token is invalid.
        :raises TypeError: if the token is None.
        '''
        raise NotImplementedError()

    @_abstractmethod
    def is_valid_user(self, username: Username) -> bool:
        '''
        Check if a username is valid, which implies the user exists.

        :param username: the username to check.
        '''
        raise NotImplementedError()


class LocalUserHandler(UserHandler):
    """
    An implementation of :class:`jgikbase.idmapping.core.user_handler.UserHandler` for users
    stored in the local database.
    """

    _LOCAL = AuthsourceID('local')

    def __init__(self, storage: IDMappingStorage) -> None:
        '''
        Create a local user handler.

        :param storage: the storage system in which users are stored.
        '''
        not_none(storage, 'storage')
        self._store = storage

    def get_authsource_id(self) -> AuthsourceID:
        return self._LOCAL

    def get_user(self, token: Token) -> User:
        not_none(token, 'token')
        # TODO ADMIN return admin status
        return User(self._LOCAL, self._store.get_user(token.get_hashed_token())[0])

    def is_valid_user(self, username: Username) -> bool:
        not_none(username, 'username')
        return self._store.user_exists(username)

    def create_user(self, username: Username) -> Token:
        '''
        Create a new user in the local storage system. Returns a new token for that user.

        :param username: The name of the user to create.
        :raises TypeError: if the user name is None.
        :raises UserExistsError: if the user already exists.
        '''
        not_none(username, 'username')
        t = tokens.generate_token()
        self._store.create_local_user(username, t.get_hashed_token())
        return t

    def new_token(self, username: Username) -> Token:
        '''
        Generate a new token for a user in the local storage system.

        :param username: The name of the user to update.
        :raises TypeError: if the user name is None.
        :raises NoSuchUserError: if the user does not exist.
        '''
        not_none(username, 'username')
        t = tokens.generate_token()
        self._store.update_local_user_token(username, t.get_hashed_token())
        return t

    def get_users(self) -> Dict[Username, bool]:
        '''
        Get the users in the local storage system.

        :returns: a mapping of username to a boolean denoting whether the user is an admin or not.
        '''
        return self._store.get_users()
