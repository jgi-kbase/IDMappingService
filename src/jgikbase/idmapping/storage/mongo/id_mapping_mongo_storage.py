"""
A MongoDB based storage system for ID mapping.
"""
from jgikbase.idmapping.storage.id_mapping_storage import IDMappingStorage as _IDMappingStorage
from jgikbase.idmapping.core.tokens import HashedToken
from jgikbase.idmapping.core.user import User, LOCAL
from pymongo.database import Database
from jgikbase.idmapping.core.util import not_none
from pymongo.errors import DuplicateKeyError, PyMongoError
import re
from jgikbase.idmapping.storage.errors import IDMappingStorageError, StorageInitException
from jgikbase.idmapping.core.errors import NoSuchUserError, UserExistsError, InvalidTokenError
from typing import Set

# TODO NOW implement remaining methods in superclass
# TODO NOW implement database schema checking

# Testing the (many) catch blocks for the general mongo exception is pretty hard, since it
# appears as though the mongo clients have a heartbeat, so just stopping mongo might trigger
# the heartbeat exception rather than the exception you're going for.

# Mocking the mongo client is probably not the answer:
# http://stackoverflow.com/questions/7413985/unit-testing-with-mongodb
# https://github.com/mockito/mockito/wiki/How-to-write-good-tests

# schema version checking constants.

# the schema version collection
_COL_CONFIG = 'config'
# the current version of the database schema.
_SCHEMA_VERSION = 1
# the key for the schema document used to ensure a singleton.
_FLD_SCHEMA_KEY = 'schema'
# the value for the schema key.
_SCHEMA_VALUE = 'schema'
# whether the schema is in the process of an update. Value is a boolean.
_FLD_SCHEMA_UPDATE = 'inupdate'
# the version of the schema. Value is _SCHEMA_VERSION.
_FLD_SCHEMA_VERSION = 'schemaver'

# database collections
_COL_USERS = 'users'

# collection fields
_FLD_AUTHSOURCE = 'auth'
_FLD_USER = 'user'
_FLD_TOKEN = 'hshtkn'

_INDEXES = {_COL_USERS: [{'idx': _FLD_USER,
                          'kw': {'unique': True},
                          },
                         {'idx': _FLD_TOKEN,
                          'kw': {'unique': True}
                          }],
            _COL_CONFIG: [{'idx': _FLD_SCHEMA_KEY,
                           'kw': {'unique': True}
                           }
                          ]
            }


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
        :raises StorageInitException: if the storage system could not be initialized properly.
        :raises MissingParameterError: if the Mongo database is None.
        """
        not_none(db, 'db')
        self._db = db
        self._ensure_indexes()
        self._check_schema()  # MUST happen after ensuring indexes

    def _ensure_indexes(self):
        try:
            for col in _INDEXES:
                for idxinfo in _INDEXES[col]:
                    self._db[col].create_index(idxinfo['idx'], **idxinfo['kw'])
        except PyMongoError as e:
            raise StorageInitException('Connection to database failed: ' + str(e)) from e

    def _check_schema(self):
        # TODO NOW
        pass

    def create_local_user(self, user: User, token: HashedToken) -> None:
        self._check_user_inputs(user, token)
        try:
            self._db[_COL_USERS].insert_one({_FLD_USER: user.username,
                                            _FLD_TOKEN: token.token_hash})
        except DuplicateKeyError as e:
            coll, index = self._get_duplicate_location(e)
            if coll == _COL_USERS:
                if index == _FLD_USER + '_1':
                    raise UserExistsError(user.username)
                elif index == _FLD_TOKEN + '_1':
                    raise ValueError('The provided token already exists in the database')
            # this is impossible to test
            raise IDMappingStorageError('Unexpected duplicate key exception')
        except PyMongoError as e:
            raise IDMappingStorageError('Connection to database failed: ' + str(e)) from e

    # this regex is gross, but matches duplicate key error text across mongo versions 2 & 3 at
    # least. Example strings:
    # 2.6 & 3
    # E11000 duplicate key error index: test_id_mapping.users.$hshtkn_1  dup key: { : "t" }
    # 3.2+
    # E11000 duplicate key error collection: test_id_mapping.users index: hshtkn_1 dup key:
    #     { : "t" }
    _DUPLICATE_KEY_REGEX = re.compile('duplicate key error (index|collection): ' +
                                      r'\w+\.(\w+)( index: |\.\$)([\.\w]+)\s+')

    def _get_duplicate_location(self, e: DuplicateKeyError):
        # To know where the duplicate key conflict occurred, we need the collection name and
        # index name for the conflict. Unfortunately that info is only available, AFAICT,
        # in the arbitrary text string that mongo sends back. There are other fields in the
        # error but they don't contain the necessary info. So it's regex time *sigh*

        # IOW, this is some shit right here, but there doesn't seem to be a better way.
        match = self._DUPLICATE_KEY_REGEX.search(e.args[0])
        if match:
            return match.group(2), match.group(4)
        else:
            # should never happen
            # the key value may be sensitive (e.g. a token) so remove it
            raise IDMappingStorageError('unable to parse duplicate key error: ' +
                                        e.args[0].split('dup key')[0])

    def _check_user_inputs(self, user, token):
        not_none(user, 'user')
        not_none(token, 'token')
        if user.authsource_id != LOCAL:
            raise ValueError('Only users from a {} authsource are allowed'
                             .format(LOCAL.id))

    def update_local_user(self, user: User, token: HashedToken) -> None:
        self._check_user_inputs(user, token)
        try:
            res = self._db[_COL_USERS].update_one({_FLD_USER: user.username},
                                                  {'$set': {_FLD_TOKEN: token.token_hash}})
            if res.matched_count != 1:  # don't care if user was updated or not, just found
                raise NoSuchUserError(user.username)
        except DuplicateKeyError as e:
            coll, index = self._get_duplicate_location(e)
            if coll == _COL_USERS and index == _FLD_TOKEN + '_1':
                raise ValueError('The provided token already exists in the database')
            # this is impossible to test
            raise IDMappingStorageError('Unexpected duplicate key exception')
        except PyMongoError as e:
            raise IDMappingStorageError('Connection to database failed: ' + str(e)) from e

    def get_user(self, token: HashedToken) -> User:
        not_none(token, 'token')
        try:
            userdoc = self._db[_COL_USERS].find_one(
                {_FLD_TOKEN: token.token_hash}, {_FLD_TOKEN: 0})
        except PyMongoError as e:
            raise IDMappingStorageError('Connection to database failed: ' + str(e)) from e

        if not userdoc:
            raise InvalidTokenError()
        return User(LOCAL, userdoc[_FLD_USER])

    def get_users(self) -> Set[User]:
        try:
            userdocs = self._db[_COL_USERS].find({}, {_FLD_TOKEN: 0})
            return {User(LOCAL, u[_FLD_USER]) for u in userdocs}
        except PyMongoError as e:
            raise IDMappingStorageError('Connection to database failed: ' + str(e)) from e
