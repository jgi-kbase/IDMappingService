"""
A MongoDB based storage system for ID mapping.
"""
from jgikbase.idmapping.storage.id_mapping_storage import IDMappingStorage as _IDMappingStorage
from jgikbase.idmapping.core.tokens import HashedToken
from jgikbase.idmapping.core.user import User, AuthsourceID
from pymongo.database import Database
from jgikbase.idmapping.util.util import not_none

# TODO NOW implement remaining methods in superclass
# TODO NOW implement database schema checking
# TODO NOW test indexes are correct
# TODO NOW finish tests

# Testing the (many) catch blocks for the general mongo exception is pretty hard, since it
# appears as though the mongo clients have a heartbeat, so just stopping mongo might trigger
# the heartbeat exception rather than the exception you're going for.

# Mocking the mongo client is probably not the answer:
# http://stackoverflow.com/questions/7413985/unit-testing-with-mongodb
# https://github.com/mockito/mockito/wiki/How-to-write-good-tests

_COL_USERS = 'users'

_FLD_AUTHSOURCE = 'auth'
_FLD_USER = 'user'
_FLD_TOKEN = 'hshtkn'


class IDMappingMongoStorage(_IDMappingStorage):
    """
    A MongoDB based implementation of
    :class:`jgikbase.idmapping.storage.id_mapping_storage.IDMappingStorage`.
    See that class for method documentation.
    """

    def __init__(self, db: Database) -> None:
        """
        Create a ID mapping storage system.

        :param db: the MongoDB database in which to store the mappings and other data.
        """
        not_none(db, 'db')
        self.db = db
        self._ensure_indexes()

    def _ensure_indexes(self):
        self.db[_COL_USERS].create_index([(_FLD_AUTHSOURCE, 1), (_FLD_USER, 1)], unique=True)
        self.db[_COL_USERS].create_index(_FLD_TOKEN, unique=True)

    def create_or_update_local_user(self, user: User, token: HashedToken) -> None:
        not_none(user, 'user')
        not_none(token, 'token')
        try:
            self.db[_COL_USERS].insert_one({_FLD_AUTHSOURCE: user.authsource.authsource,
                                            _FLD_USER: user.username,
                                            _FLD_TOKEN: token.token_hash})
        except Exception as e:
            # TODO EXCEP handle duplicate user, token
            # TODO EXCEP handle other mongo errors
            raise e

    def get_user(self, token: HashedToken) -> User:
        not_none(token, 'token')
        try:
            userdoc = self.db[_COL_USERS].find_one({_FLD_TOKEN: token.token_hash}, {_FLD_TOKEN: 0})
        except Exception as e:
            # TODO EXCEP handle other mongo errors
            raise e

        if not userdoc:
            raise ValueError('Invalid token')  # TODO EXCEP use specific exception
        return User(AuthsourceID(userdoc[_FLD_AUTHSOURCE]), userdoc[_FLD_USER])
