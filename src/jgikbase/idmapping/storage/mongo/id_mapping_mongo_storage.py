"""
A MongoDB based storage system for ID mapping.
"""
from jgikbase.idmapping.storage.id_mapping_storage import IDMappingStorage as _IDMappingStorage
from jgikbase.idmapping.core.tokens import HashedToken
from jgikbase.idmapping.core.user import User, LOCAL
from pymongo.database import Database
from jgikbase.idmapping.util.util import not_none
from pymongo.errors import DuplicateKeyError, PyMongoError
import re

# TODO NOW implement remaining methods in superclass
# TODO NOW implement database schema checking

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
        self.db[_COL_USERS].create_index(_FLD_USER, unique=True)
        self.db[_COL_USERS].create_index(_FLD_TOKEN, unique=True)

    def create_local_user(self, user: User, token: HashedToken) -> None:
        self._check_user_inputs(user, token)
        try:
            self.db[_COL_USERS].insert_one({_FLD_USER: user.username,
                                            _FLD_TOKEN: token.token_hash})
        except DuplicateKeyError as e:
            coll, index = self._get_duplicate_location(e)
            if coll == _COL_USERS:
                if index == _FLD_USER + '_1':
                    # TODO EXCEP make duplicate user exception
                    raise ValueError('Duplicate user: ' + user.username)
                elif index == _FLD_TOKEN + '_1':
                    # TODO EXCEP make duplicate token exception
                    raise ValueError('The provided token already exists in the database')
            # this is impossible to test
            raise ValueError('Unexpected duplicate key exception')
        except PyMongoError as e:
            # TODO EXCEP handle other mongo errors
            raise e

    # this regex is gross, but matches duplicate key error text across mongo versions 2 & 3 at
    # least.
    _DUPLICATE_KEY_REGEX = re.compile('duplicate key error (index|collection): ' +
                                      '\\w+\\.(\\w+)( index: |\\.\\$)([\\.\\w]+)\\s+')

    def _get_duplicate_location(self, e: DuplicateKeyError):
        # this is some shit right here, but there doesn't seem to be a better way.
        match = self._DUPLICATE_KEY_REGEX.search(e.args[0])
        if match:
            return match.group(2), match.group(4)
        else:
            # the key value may be sensitive (e.g. a token) so remove it
            # TODO EXCEP change to appropriate exception
            raise ValueError('unable to parse duplicate key error: ' +
                             e.args[0].split('dup key')[0])

    def _check_user_inputs(self, user, token):
        not_none(user, 'user')
        not_none(token, 'token')
        if user.authsource != LOCAL:
            raise ValueError('Only users from a {} authsource are allowed'
                             .format(LOCAL.authsource))

    def update_local_user(self, user: User, token: HashedToken) -> None:
        self._check_user_inputs(user, token)
        try:
            res = self.db[_COL_USERS].update_one({_FLD_USER: user.username},
                                                 {'$set': {_FLD_TOKEN: token.token_hash}})
            if res.matched_count != 1:  # don't care if user was updated or not, just found
                # TODO EXCEP make user not found exception
                raise ValueError('No such user: ' + user.username)
        except DuplicateKeyError as e:
            coll, index = self._get_duplicate_location(e)
            if coll == _COL_USERS and index == _FLD_TOKEN + '_1':
                # TODO EXCEP make duplicate token exception
                raise ValueError('The provided token already exists in the database')
            # this is impossible to test
            raise ValueError('Unexpected duplicate key exception')
        except PyMongoError as e:
            # TODO EXCEP handle other mongo errors
            raise e

    def get_user(self, token: HashedToken) -> User:
        not_none(token, 'token')
        try:
            userdoc = self.db[_COL_USERS].find_one({_FLD_TOKEN: token.token_hash}, {_FLD_TOKEN: 0})
        except PyMongoError as e:
            # TODO EXCEP handle other mongo errors
            raise e

        if not userdoc:
            raise ValueError('Invalid token')  # TODO EXCEP use specific exception
        return User(LOCAL, userdoc[_FLD_USER])
