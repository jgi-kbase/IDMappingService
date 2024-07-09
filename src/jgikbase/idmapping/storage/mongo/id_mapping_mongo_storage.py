"""
A MongoDB based storage system for ID mapping.
"""

from jgikbase.idmapping.storage.id_mapping_storage import (
    IDMappingStorage as _IDMappingStorage,
)
from jgikbase.idmapping.core.tokens import HashedToken
from jgikbase.idmapping.core.user import User, AuthsourceID, Username
from pymongo.database import Database
from jgikbase.idmapping.core.arg_check import not_none, no_Nones_in_iterable
from pymongo.errors import DuplicateKeyError, PyMongoError
import re
from jgikbase.idmapping.storage.errors import (
    IDMappingStorageError,
    StorageInitException,
)
from jgikbase.idmapping.core.errors import (
    NoSuchUserError,
    UserExistsError,
    InvalidTokenError,
    NamespaceExistsError,
    NoSuchNamespaceError,
)
from typing import (
    Set,
    Iterable,
    Tuple,
    Dict,
    Any,
    List,
    Optional,
)  # @UnusedImport pydev gets confused here
from jgikbase.idmapping.core.object_id import NamespaceID, Namespace, ObjectID

# Testing the (many) catch blocks for the general mongo exception is pretty hard, since it
# appears as though the mongo clients have a heartbeat, so just stopping mongo might trigger
# the heartbeat exception rather than the exception you're going for.

# Mocking the mongo client is probably not the answer:
# http://stackoverflow.com/questions/7413985/unit-testing-with-mongodb
# https://github.com/mockito/mockito/wiki/How-to-write-good-tests

# schema version checking constants.

# the schema version collection
_COL_CONFIG = "config"
# the current version of the database schema.
_SCHEMA_VERSION = 1
# the key for the schema document used to ensure a singleton.
_FLD_SCHEMA_KEY = "schema"
# the value for the schema key.
_SCHEMA_VALUE = "schema"
# whether the schema is in the process of an update. Value is a boolean.
_FLD_SCHEMA_UPDATE = "inupdate"
# the version of the schema. Value is _SCHEMA_VERSION.
_FLD_SCHEMA_VERSION = "schemaver"

# database collections
_COL_USERS = "users"
_COL_NAMESPACES = "ns"
_COL_MAPPINGS = "map"

# user collection fields
_FLD_AUTHSOURCE = "auth"
_FLD_USER = "user"
_FLD_TOKEN = "hshtkn"  # nosec
_FLD_ADMIN = "admin"

# namespace collection fields
_FLD_NS_ID = "nsid"
_FLD_PUB_MAP = "pubmap"
_FLD_USERS = "users"
_FLD_AUTHSOURCE = "auth"
_FLD_NAME = "name"

# mapping collection fields:
_FLD_PRIMARY_NS = "pnsid"
_FLD_SECONDARY_NS = "snsid"
_FLD_PRIMARY_ID = "pid"
_FLD_SECONDARY_ID = "sid"

_INDEXES = {
    _COL_USERS: [
        {
            "idx": _FLD_USER,
            "kw": {"unique": True},
        },
        {"idx": _FLD_TOKEN, "kw": {"unique": True}},
    ],
    _COL_NAMESPACES: [{"idx": _FLD_NS_ID, "kw": {"unique": True}}],
    _COL_MAPPINGS: [
        {
            "idx": [
                (_FLD_PRIMARY_NS, 1),
                (_FLD_PRIMARY_ID, 1),
                (_FLD_SECONDARY_NS, 1),
                (_FLD_SECONDARY_ID, 1),
            ],
            "kw": {"unique": True},
        },
        # index for 'backwards' queries
        # could improve performance by including the primary IDs for covered
        # queries. Not sure if that's worth the index size increase.
        {"idx": [(_FLD_SECONDARY_NS, 1), (_FLD_SECONDARY_ID, 1)], "kw": {}},
    ],
    _COL_CONFIG: [{"idx": _FLD_SCHEMA_KEY, "kw": {"unique": True}}],
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
        :raises TypeError: if the Mongo database is None.
        """
        not_none(db, "db")
        self._db = db
        self._ensure_indexes()
        self._check_schema()  # MUST happen after ensuring indexes

    def _ensure_indexes(self):
        try:
            for col in _INDEXES:
                for idxinfo in _INDEXES[col]:
                    self._db[col].create_index(idxinfo["idx"], **idxinfo["kw"])
        except PyMongoError as e:
            raise StorageInitException("Failed to create index: " + str(e)) from e

    def _check_schema(self):
        col = self._db[_COL_CONFIG]
        try:
            col.insert_one(
                {
                    _FLD_SCHEMA_KEY: _SCHEMA_VALUE,
                    _FLD_SCHEMA_UPDATE: False,
                    _FLD_SCHEMA_VERSION: _SCHEMA_VERSION,
                }
            )
        except DuplicateKeyError:
            # ok, the schema version document is already there, this isn't the first time this
            # database as been used. Now check the document is ok.
            if col.count() != 1:
                raise StorageInitException(
                    "Multiple config objects found in the database. "
                    + "This should not happen, something is very wrong."
                )
            cfgdoc = col.find_one({_FLD_SCHEMA_KEY: _SCHEMA_VALUE})
            if cfgdoc[_FLD_SCHEMA_VERSION] != _SCHEMA_VERSION:
                raise StorageInitException(
                    "Incompatible database schema. Server is v{}, DB is v{}".format(
                        _SCHEMA_VERSION, cfgdoc[_FLD_SCHEMA_VERSION]
                    )
                )
            if cfgdoc[_FLD_SCHEMA_UPDATE]:
                raise StorageInitException(
                    "The database is in the middle of an update from "
                    + "v{} of the schema. Aborting startup.".format(
                        cfgdoc[_FLD_SCHEMA_VERSION]
                    )
                )
        except PyMongoError as e:
            raise StorageInitException(
                "Connection to database failed: " + str(e)
            ) from e

    def create_local_user(self, username: Username, token: HashedToken) -> None:
        not_none(username, "username")
        not_none(token, "token")
        try:
            self._db[_COL_USERS].insert_one(
                {
                    _FLD_USER: username.name,
                    _FLD_TOKEN: token.token_hash,
                    _FLD_ADMIN: False,
                }
            )
        except DuplicateKeyError as e:
            coll, index = self._get_duplicate_location(e)
            if coll == _COL_USERS:
                if index == _FLD_USER + "_1":
                    raise UserExistsError(username.name)
                elif index == _FLD_TOKEN + "_1":
                    raise ValueError(
                        "The provided token already exists in the database"
                    )
            # this is impossible to test
            raise IDMappingStorageError("Unexpected duplicate key exception")
        except PyMongoError as e:
            raise IDMappingStorageError(
                "Connection to database failed: " + str(e)
            ) from e

    def set_local_user_as_admin(self, username: Username, admin: bool) -> None:
        not_none(username, "username")
        admin = True if admin else False  # more readable than admin and True
        try:
            res = self._db[_COL_USERS].update_one(
                {_FLD_USER: username.name}, {"$set": {_FLD_ADMIN: admin}}
            )
            if (
                res.matched_count != 1
            ):  # don't care if user was updated or not, just found
                raise NoSuchUserError(username.name)
        except PyMongoError as e:
            raise IDMappingStorageError(
                "Connection to database failed: " + str(e)
            ) from e

    # this regex is gross, but matches duplicate key error text across mongo versions 2 & 3 at
    # least. Example strings:
    # 2.6 & 3
    # E11000 duplicate key error index: test_id_mapping.users.$hshtkn_1  dup key: { : "t" }
    # 3.2+
    # E11000 duplicate key error collection: test_id_mapping.users index: hshtkn_1 dup key:
    #     { : "t" }
    _DUPLICATE_KEY_REGEX = re.compile(
        "duplicate key error (index|collection): "
        + r"\w+\.(\w+)( index: |\.\$)([\.\w]+)\s+"
    )

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
            raise IDMappingStorageError(
                "unable to parse duplicate key error: " + e.args[0].split("dup key")[0]
            )

    def update_local_user_token(self, username: Username, token: HashedToken) -> None:
        not_none(username, "username")
        not_none(token, "token")
        try:
            res = self._db[_COL_USERS].update_one(
                {_FLD_USER: username.name}, {"$set": {_FLD_TOKEN: token.token_hash}}
            )
            if (
                res.matched_count != 1
            ):  # don't care if user was updated or not, just found
                raise NoSuchUserError(username.name)
        except DuplicateKeyError:
            # since only the token can cause a duplicate key error here, we assume something
            # crazy isn't going and just raise that exception
            raise ValueError("The provided token already exists in the database")
        except PyMongoError as e:
            raise IDMappingStorageError(
                "Connection to database failed: " + str(e)
            ) from e

    def get_user(self, token: HashedToken) -> Tuple[Username, bool]:
        not_none(token, "token")
        try:
            userdoc = self._db[_COL_USERS].find_one(
                {_FLD_TOKEN: token.token_hash}, {_FLD_TOKEN: 0}
            )
        except PyMongoError as e:
            raise IDMappingStorageError(
                "Connection to database failed: " + str(e)
            ) from e

        if not userdoc:
            raise InvalidTokenError()
        return (Username(userdoc[_FLD_USER]), userdoc[_FLD_ADMIN])

    def get_users(self) -> Dict[Username, bool]:
        try:
            userdocs = self._db[_COL_USERS].find({}, {_FLD_TOKEN: 0})
            return {Username(u[_FLD_USER]): u[_FLD_ADMIN] for u in userdocs}
        except PyMongoError as e:
            raise IDMappingStorageError(
                "Connection to database failed: " + str(e)
            ) from e

    def user_exists(self, username: Username) -> bool:
        not_none(username, "username")
        try:
            return self._db[_COL_USERS].count_documents({_FLD_USER: username.name}) == 1
        except PyMongoError as e:
            raise IDMappingStorageError(
                "Connection to database failed: " + str(e)
            ) from e

    def create_namespace(self, namespace_id: NamespaceID) -> None:
        not_none(namespace_id, "namespace_id")
        try:
            self._db[_COL_NAMESPACES].insert_one(
                {_FLD_NS_ID: namespace_id.id, _FLD_PUB_MAP: False, _FLD_USERS: []}
            )
        except DuplicateKeyError:
            raise NamespaceExistsError(namespace_id.id)
        except PyMongoError as e:
            raise IDMappingStorageError(
                "Connection to database failed: " + str(e)
            ) from e

    def get_namespace(self, namespace_id: NamespaceID) -> Namespace:
        not_none(namespace_id, "namespace_id")
        try:
            nsdoc = self._db[_COL_NAMESPACES].find_one({_FLD_NS_ID: namespace_id.id})
        except PyMongoError as e:
            raise IDMappingStorageError(
                "Connection to database failed: " + str(e)
            ) from e

        if not nsdoc:
            raise NoSuchNamespaceError(namespace_id.id)
        return self._to_ns(nsdoc)

    def _to_user_set(self, userdocs) -> Set[User]:
        return {
            User(AuthsourceID(u[_FLD_AUTHSOURCE]), Username(u[_FLD_NAME]))
            for u in userdocs
        }

    def add_user_to_namespace(
        self, namespace_id: NamespaceID, admin_user: User
    ) -> None:
        self._modify_namespace_users(True, namespace_id, admin_user)

    def remove_user_from_namespace(
        self, namespace_id: NamespaceID, admin_user: User
    ) -> None:
        self._modify_namespace_users(False, namespace_id, admin_user)

    def _modify_namespace_users(self, add: bool, namespace_id, admin_user):
        """
        :param add: True to add the user to the namespace, False to remove.
        """
        not_none(namespace_id, "namespace_id")
        not_none(admin_user, "admin_user")
        op = "$addToSet" if add else "$pull"
        try:
            res = self._db[_COL_NAMESPACES].update_one(
                {_FLD_NS_ID: namespace_id.id},
                {
                    op: {
                        _FLD_USERS: {
                            _FLD_AUTHSOURCE: admin_user.authsource_id.id,
                            _FLD_NAME: admin_user.username.name,
                        }
                    }
                },
            )
            if res.matched_count != 1:
                raise NoSuchNamespaceError(namespace_id.id)
            if res.modified_count != 1:
                action = "already administrates" if add else "does not administrate"
                ex = (
                    UserExistsError if add else NoSuchUserError
                )  # might want diff exceps here
                raise ex(
                    "User {}/{} {} namespace {}".format(
                        admin_user.authsource_id.id,
                        admin_user.username.name,
                        action,
                        namespace_id.id,
                    )
                )
        except PyMongoError as e:
            raise IDMappingStorageError(
                "Connection to database failed: " + str(e)
            ) from e

    def set_namespace_publicly_mappable(
        self, namespace_id: NamespaceID, publicly_mappable: bool
    ) -> None:
        not_none(namespace_id, "namespace_id")
        pm = True if publicly_mappable else False  # more readable than 'and True'
        try:
            res = self._db[_COL_NAMESPACES].update_one(
                {_FLD_NS_ID: namespace_id.id}, {"$set": {_FLD_PUB_MAP: pm}}
            )
            if res.matched_count != 1:  # don't care if modified or not
                raise NoSuchNamespaceError(namespace_id.id)
        except PyMongoError as e:
            raise IDMappingStorageError(
                "Connection to database failed: " + str(e)
            ) from e

    def get_namespaces(self, nids: Optional[Iterable[NamespaceID]] = None) -> Set[Namespace]:
        query = {}
        nidstr: List[str] = []
        if nids:
            no_Nones_in_iterable(nids, "nids")
            nidstr = [nid.id for nid in nids]
            query[_FLD_NS_ID] = {"$in": nidstr}
        try:
            nsdocs = self._db[_COL_NAMESPACES].find(query)
            nsobjs = {self._to_ns(nsdoc) for nsdoc in nsdocs}
            if nidstr and len(nsobjs) != len(nidstr):
                missing = set(nidstr) - {ns.namespace_id.id for ns in nsobjs}
                raise NoSuchNamespaceError(str(sorted(missing)))
            return nsobjs
        except PyMongoError as e:
            raise IDMappingStorageError(
                "Connection to database failed: " + str(e)
            ) from e

    def _to_ns(self, nsdoc):
        return Namespace(
            NamespaceID(nsdoc[_FLD_NS_ID]),
            nsdoc[_FLD_PUB_MAP],
            self._to_user_set(nsdoc[_FLD_USERS]),
        )

    def add_mapping(self, primary_OID: ObjectID, secondary_OID: ObjectID) -> None:
        not_none(primary_OID, "primary_OID")
        not_none(secondary_OID, "secondary_OID")
        try:
            self._db[_COL_MAPPINGS].insert_one(
                self.to_mapping_mongo_doc(primary_OID, secondary_OID)
            )
        except DuplicateKeyError:
            pass  # don't care, record is already there
        except PyMongoError as e:
            raise IDMappingStorageError(
                "Connection to database failed: " + str(e)
            ) from e

    def to_mapping_mongo_doc(self, primary_OID, secondary_OID):
        return {
            _FLD_PRIMARY_NS: primary_OID.namespace_id.id,
            _FLD_PRIMARY_ID: primary_OID.id,
            _FLD_SECONDARY_NS: secondary_OID.namespace_id.id,
            _FLD_SECONDARY_ID: secondary_OID.id,
        }

    def remove_mapping(self, primary_OID: ObjectID, secondary_OID: ObjectID) -> bool:
        not_none(primary_OID, "primary_OID")
        not_none(secondary_OID, "secondary_OID")
        try:
            res = self._db[_COL_MAPPINGS].delete_one(
                self.to_mapping_mongo_doc(primary_OID, secondary_OID)
            )
            return res.deleted_count == 1
        except PyMongoError as e:
            raise IDMappingStorageError(
                "Connection to database failed: " + str(e)
            ) from e

    def find_mappings(
        self, oid: ObjectID, ns_filter: Optional[Iterable[NamespaceID]] = None
    ) -> Tuple[Set[ObjectID], Set[ObjectID]]:
        not_none(oid, "oid")
        # could probably make a method & run it twice here but not worth the trouble
        primary_query: Dict[str, Any] = {
            _FLD_PRIMARY_NS: oid.namespace_id.id,
            _FLD_PRIMARY_ID: oid.id,
        }
        secondary_query: Dict[str, Any] = {
            _FLD_SECONDARY_NS: oid.namespace_id.id,
            _FLD_SECONDARY_ID: oid.id,
        }
        if ns_filter:
            no_Nones_in_iterable(ns_filter, "ns_filter")
            fil = [ns.id for ns in ns_filter]
            primary_query[_FLD_SECONDARY_NS] = {"$in": fil}
            secondary_query[_FLD_PRIMARY_NS] = {"$in": fil}
        try:
            mappings = self._db[_COL_MAPPINGS].find(
                primary_query, {_FLD_PRIMARY_NS: 0, _FLD_PRIMARY_ID: 0}
            )
            primary = {
                ObjectID(NamespaceID(m[_FLD_SECONDARY_NS]), m[_FLD_SECONDARY_ID])
                for m in mappings
            }
            mappings = self._db[_COL_MAPPINGS].find(
                secondary_query, {_FLD_SECONDARY_NS: 0, _FLD_SECONDARY_ID: 0}
            )
            secondary = {
                ObjectID(NamespaceID(m[_FLD_PRIMARY_NS]), m[_FLD_PRIMARY_ID])
                for m in mappings
            }
            return primary, secondary
            # nothing to check here. As long as the op doesn't fail we're good
        except PyMongoError as e:
            raise IDMappingStorageError(
                "Connection to database failed: " + str(e)
            ) from e
