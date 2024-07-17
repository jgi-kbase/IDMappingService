from pytest import raises, fixture
from jgikbase.test.idmapping.mongo_controller import MongoController
from jgikbase.test.idmapping import test_utils
from jgikbase.idmapping.storage.mongo.id_mapping_mongo_storage import (
    IDMappingMongoStorage,
)
from jgikbase.idmapping.core.user import User, AuthsourceID, Username
from jgikbase.idmapping.core.tokens import HashedToken
from jgikbase.test.idmapping.test_utils import assert_exception_correct
from pymongo.errors import DuplicateKeyError
from jgikbase.idmapping.core.errors import (
    NoSuchUserError,
    UserExistsError,
    InvalidTokenError,
    NamespaceExistsError,
    NoSuchNamespaceError,
)
from jgikbase.idmapping.storage.errors import (
    IDMappingStorageError,
    StorageInitException,
)
import re
from jgikbase.idmapping.core.object_id import NamespaceID, Namespace, ObjectID

TEST_DB_NAME = "test_id_mapping"


@fixture(scope="module")
def mongo():
    mongoexe = test_utils.get_mongo_exe()
    tempdir = test_utils.get_temp_dir()
    wt = test_utils.get_use_wired_tiger()
    mongo = MongoController(mongoexe, tempdir, wt)
    print(
        "running mongo {}{} on port {} in dir {}".format(
            mongo.db_version,
            " with WiredTiger" if wt else "",
            mongo.port,
            mongo.temp_dir,
        )
    )
    yield mongo
    del_temp = test_utils.get_delete_temp_files()
    print("shutting down mongo, delete_temp_files={}".format(del_temp))
    mongo.destroy(del_temp)


@fixture
def idstorage(mongo):
    mongo.clear_database(TEST_DB_NAME, drop_indexes=True)
    return IDMappingMongoStorage(mongo.client[TEST_DB_NAME])


def test_fail_startup():
    with raises(Exception) as got:
        IDMappingMongoStorage(None)
    assert_exception_correct(got.value, TypeError("db cannot be None"))


# The following tests ensure that all indexes are created correctly. The collection names
# are tested so that if a new collection is added the test will fail without altering
# said test, at which time the coder will hopefully read this notice and add index tests
# for the new collection.


def test_collection_names(idstorage, mongo):
    names = mongo.client[TEST_DB_NAME].list_collection_names()
    expected = set(["users", "config", "ns", "map"])
    if mongo.includes_system_indexes:
        expected.add("system.indexes")
    assert set(names) == expected


def test_index_config(idstorage, mongo):
    v = mongo.index_version
    indexes = mongo.client[TEST_DB_NAME]["config"].index_information()
    test_utils.remove_ns_from_index_info(indexes)
    expected = {
        "_id_": {"v": v, "key": [("_id", 1)]},
        "schema_1": {
            "v": v,
            "unique": True,
            "key": [("schema", 1)],
        },
    }
    assert indexes == expected


def test_index_user(idstorage, mongo):
    v = mongo.index_version
    indexes = mongo.client[TEST_DB_NAME]["users"].index_information()
    test_utils.remove_ns_from_index_info(indexes)
    expected = {
        "_id_": {"v": v, "key": [("_id", 1)]},
        "user_1": {
            "v": v,
            "unique": True,
            "key": [("user", 1)],
        },
        "hshtkn_1": {
            "v": v,
            "unique": True,
            "key": [("hshtkn", 1)],
        },
    }
    assert indexes == expected


def test_index_namespace(idstorage, mongo):
    v = mongo.index_version
    indexes = mongo.client[TEST_DB_NAME]["ns"].index_information()
    test_utils.remove_ns_from_index_info(indexes)
    expected = {
        "_id_": {"v": v, "key": [("_id", 1)]},
        "nsid_1": {
            "v": v,
            "unique": True,
            "key": [("nsid", 1)],
        },
    }
    assert indexes == expected


def test_index_mappings(idstorage, mongo):
    v = mongo.index_version
    indexes = mongo.client[TEST_DB_NAME]["map"].index_information()
    test_utils.remove_ns_from_index_info(indexes)
    expected = {
        "_id_": {"v": v, "key": [("_id", 1)]},
        "pnsid_1_pid_1_snsid_1_sid_1": {
            "v": v,
            "unique": True,
            "key": [("pnsid", 1), ("pid", 1), ("snsid", 1), ("sid", 1)],
        },
        "snsid_1_sid_1": {
            "v": v,
            "key": [("snsid", 1), ("sid", 1)],
        },
    }
    assert indexes == expected


def test_startup_and_check_config_doc(idstorage, mongo):
    col = mongo.client[TEST_DB_NAME]["config"]
    assert len(list(col.find({}))) == 1  # only one config doc
    cfgdoc = col.find_one()
    assert cfgdoc["schema"] == "schema"
    assert cfgdoc["schemaver"] == 1
    assert cfgdoc["inupdate"] is False

    # check startup works with cfg object in place
    idmap = IDMappingMongoStorage(mongo.client[TEST_DB_NAME])
    idmap.create_local_user(Username("foo"), HashedToken("t"))
    assert idmap.get_user(HashedToken("t")) == (Username("foo"), False)


def test_startup_with_2_config_docs(mongo):
    col = mongo.client[TEST_DB_NAME]["config"]
    col.drop()  # clear db independently of creating a idmapping mongo instance
    col.insert_many(
        [
            {"schema": "schema", "schemaver": 1, "inupdate": False},
            {"schema": "schema", "schemaver": 2, "inupdate": False},
        ]
    )

    # pattern matcher for the error format across python 2 & 3
    p = re.compile(
        r'Failed to create index: .*?'
        r'E11000 duplicate key error collection: test_id_mapping.config index: schema_1 '
        r'dup key: (\{ : "schema" \}|\{ schema: "schema" \})'
    )

    with raises(StorageInitException) as got:
        IDMappingMongoStorage(mongo.client[TEST_DB_NAME])
    assert p.match(got.value.args[0]) is not None


def test_startup_with_extra_corrupt_config_doc(mongo):
    col = mongo.client[TEST_DB_NAME]["config"]
    col.drop()  # clear db independently of creating a idmapping mongo instance
    col.insert_many(
        [
            {"schema": "schema", "schemaver": 1, "inupdate": False},
            {"schema": "schemabad", "schemaver": 2, "inupdate": False},
        ]
    )

    fail_startup(
        mongo,
        "Multiple config objects found in the database. "
        + "This should not happen, something is very wrong.",
    )


def test_startup_with_bad_schema_version(mongo):
    col = mongo.client[TEST_DB_NAME]["config"]
    col.drop()  # clear db independently of creating a idmapping mongo instance
    col.insert_one({"schema": "schema", "schemaver": 4, "inupdate": False})

    fail_startup(mongo, "Incompatible database schema. Server is v1, DB is v4")


def test_startup_in_update(mongo):
    col = mongo.client[TEST_DB_NAME]["config"]
    col.drop()  # clear db independently of creating a idmapping mongo instance
    col.insert_one({"schema": "schema", "schemaver": 1, "inupdate": True})

    fail_startup(
        mongo,
        "The database is in the middle of an update from v1 of the "
        + "schema. Aborting startup.",
    )


def fail_startup(mongo, expected_msg):
    with raises(Exception) as got:
        IDMappingMongoStorage(mongo.client[TEST_DB_NAME])
    assert_exception_correct(got.value, StorageInitException(expected_msg))


def test_create_update_and_get_user(idstorage):
    # create
    idstorage.create_local_user(Username("foo"), HashedToken("bar"))
    assert idstorage.get_user(HashedToken("bar")) == (Username("foo"), False)

    # update
    idstorage.update_local_user_token(Username("foo"), HashedToken("bat"))
    assert idstorage.get_user(HashedToken("bat")) == (Username("foo"), False)

    idstorage.update_local_user_token(Username("foo"), HashedToken("boo"))
    assert idstorage.get_user(HashedToken("boo")) == (Username("foo"), False)

    # test different user
    idstorage.create_local_user(Username("foo1"), HashedToken("baz"))
    assert idstorage.get_user(HashedToken("baz")) == (Username("foo1"), False)


def test_create_user_fail_input_None(idstorage):
    t = HashedToken("t")
    u = Username("u")
    fail_create_user(idstorage, None, t, TypeError("username cannot be None"))
    fail_create_user(idstorage, u, None, TypeError("token cannot be None"))


def test_create_user_fail_duplicate_user(idstorage):
    idstorage.create_local_user(Username("u"), HashedToken("t"))
    fail_create_user(idstorage, Username("u"), HashedToken("t1"), UserExistsError("u"))


def test_create_user_fail_duplicate_token(idstorage):
    idstorage.create_local_user(Username("u"), HashedToken("t"))
    fail_create_user(
        idstorage,
        Username("u1"),
        HashedToken("t"),
        ValueError("The provided token already exists in the database"),
    )


def fail_create_user(idstorage, user, token, expected):
    with raises(Exception) as got:
        idstorage.create_local_user(user, token)
    assert_exception_correct(got.value, expected)


def test_update_user_token_fail_input_None(idstorage):
    t = HashedToken("t")
    u = Username("u")
    fail_update_user_token(idstorage, None, t, TypeError("username cannot be None"))
    fail_update_user_token(idstorage, u, None, TypeError("token cannot be None"))


def test_update_user_token_fail_duplicate_token(idstorage):
    idstorage.create_local_user(Username("u"), HashedToken("t"))
    idstorage.create_local_user(Username("u1"), HashedToken("t1"))
    fail_update_user_token(
        idstorage,
        Username("u1"),
        HashedToken("t"),
        ValueError("The provided token already exists in the database"),
    )


def test_update_user_token_fail_no_such_user(idstorage):
    idstorage.create_local_user(Username("u"), HashedToken("t"))
    fail_update_user_token(
        idstorage, Username("u1"), HashedToken("t1"), NoSuchUserError("u1")
    )


def fail_update_user_token(idstorage, user, token, expected):
    with raises(Exception) as got:
        idstorage.update_local_user_token(user, token)
    assert_exception_correct(got.value, expected)


def test_get_user_fail_input_None(idstorage):
    fail_get_user(idstorage, None, TypeError("token cannot be None"))


def test_get_user_fail_no_such_token(idstorage):
    idstorage.create_local_user(Username("u"), HashedToken("t"))
    fail_get_user(idstorage, HashedToken("t1"), InvalidTokenError())


def fail_get_user(idstorage, token, expected):
    with raises(Exception) as got:
        idstorage.get_user(token)
    assert_exception_correct(got.value, expected)


def test_set_user_as_admin(idstorage):
    idstorage.create_local_user(Username("foo"), HashedToken("bar"))

    assert idstorage.get_user(HashedToken("bar")) == (Username("foo"), False)

    # set twice to check 2nd is no-op
    idstorage.set_local_user_as_admin(Username("foo"), True)
    idstorage.set_local_user_as_admin(Username("foo"), True)

    assert idstorage.get_user(HashedToken("bar")) == (Username("foo"), True)

    idstorage.set_local_user_as_admin(Username("foo"), False)
    idstorage.set_local_user_as_admin(Username("foo"), False)

    assert idstorage.get_user(HashedToken("bar")) == (Username("foo"), False)

    idstorage.set_local_user_as_admin(Username("foo"), True)
    idstorage.set_local_user_as_admin(Username("foo"), None)

    assert idstorage.get_user(HashedToken("bar")) == (Username("foo"), False)


def test_set_local_user_as_admin_fail_None_input(idstorage):
    fail_set_local_user_as_admin(idstorage, None, TypeError("username cannot be None"))


def test_set_local_user_as_admin_fail_no_such_user(idstorage):
    idstorage.create_local_user(Username("bar"), HashedToken("whoo"))
    fail_set_local_user_as_admin(idstorage, Username("foo"), NoSuchUserError("foo"))


def fail_set_local_user_as_admin(idstorage, user, expected):
    with raises(Exception) as got:
        idstorage.set_local_user_as_admin(user, True)
    assert_exception_correct(got.value, expected)


def test_unparseable_duplicate_key_exception(idstorage):
    # this is a very naughty test reaching into the implementation
    with raises(Exception) as got:
        idstorage._get_duplicate_location(DuplicateKeyError("unmatchable dup key foo"))
        assert_exception_correct(
            got.value,
            IDMappingStorageError("unable to parse duplicate key error: unmatchable "),
        )


def test_get_users(idstorage):
    assert idstorage.get_users() == {}

    idstorage.create_local_user(Username("foo"), HashedToken("t1"))

    assert idstorage.get_users() == {Username("foo"): False}

    idstorage.create_local_user(Username("mrsentity"), HashedToken("t2"))
    idstorage.create_local_user(Username("mrsenigma"), HashedToken("t3"))
    idstorage.update_local_user_token(Username("mrsenigma"), HashedToken("t4"))

    idstorage.set_local_user_as_admin(Username("foo"), True)
    idstorage.set_local_user_as_admin(Username("mrsenigma"), True)

    assert idstorage.get_users() == {
        Username("foo"): True,
        Username("mrsenigma"): True,
        Username("mrsentity"): False,
    }


def test_user_exists(idstorage):
    idstorage.create_local_user(Username("foo"), HashedToken("t1"))

    assert idstorage.user_exists(Username("foo")) is True
    assert idstorage.user_exists(Username("bar")) is False


def test_user_exists_fail(idstorage):
    with raises(Exception) as got:
        idstorage.user_exists(None)
    assert_exception_correct(got.value, TypeError("username cannot be None"))


def test_create_and_get_namespace(idstorage):
    idstorage.create_namespace(NamespaceID("foo"))
    expected = Namespace(NamespaceID("foo"), False, None)

    assert idstorage.get_namespace(NamespaceID("foo")) == expected

    idstorage.create_namespace(NamespaceID("bar"))
    expected = Namespace(NamespaceID("bar"), False, None)

    assert idstorage.get_namespace(NamespaceID("bar")) == expected


def test_create_namespace_fail_input_None(idstorage):
    fail_create_namespace(idstorage, None, TypeError("namespace_id cannot be None"))


def test_create_namespace_fail_namespace_exists(idstorage):
    idstorage.create_namespace(NamespaceID("foo"))

    fail_create_namespace(idstorage, NamespaceID("foo"), NamespaceExistsError("foo"))


def fail_create_namespace(idstorage, namespace_id, expected):
    with raises(Exception) as got:
        idstorage.create_namespace(namespace_id)
    assert_exception_correct(got.value, expected)


def test_get_namespace_fail_input_None(idstorage):
    fail_get_namespace(idstorage, None, TypeError("namespace_id cannot be None"))


def test_get_namespace_fail_no_such_namespace(idstorage):
    idstorage.create_namespace(NamespaceID("foo"))
    fail_get_namespace(idstorage, NamespaceID("bar"), NoSuchNamespaceError("bar"))


def fail_get_namespace(idstorage, namespace_id, expected):
    with raises(Exception) as got:
        idstorage.get_namespace(namespace_id)
    assert_exception_correct(got.value, expected)


def test_add_and_remove_namespace_users(idstorage):
    nsid = NamespaceID("foo")
    idstorage.create_namespace(nsid)
    assert idstorage.get_namespace(NamespaceID("foo")) == Namespace(
        NamespaceID("foo"), False
    )

    idstorage.add_user_to_namespace(nsid, User(AuthsourceID("asone"), Username("u1")))
    users = set([User(AuthsourceID("asone"), Username("u1"))])
    assert idstorage.get_namespace(nsid) == Namespace(NamespaceID("foo"), False, users)

    idstorage.add_user_to_namespace(nsid, User(AuthsourceID("astwo"), Username("u2")))
    users.add(User(AuthsourceID("astwo"), Username("u2")))
    assert idstorage.get_namespace(nsid) == Namespace(NamespaceID("foo"), False, users)

    idstorage.remove_user_from_namespace(
        NamespaceID("foo"), User(AuthsourceID("asone"), Username("u1"))
    )
    users = set([User(AuthsourceID("astwo"), Username("u2"))])
    assert idstorage.get_namespace(nsid) == Namespace(NamespaceID("foo"), False, users)

    idstorage.remove_user_from_namespace(
        NamespaceID("foo"), User(AuthsourceID("astwo"), Username("u2"))
    )
    assert idstorage.get_namespace(nsid) == Namespace(NamespaceID("foo"), False)


def test_add_user_to_namespace_fail_inputs_None(idstorage):
    u = User(AuthsourceID("as"), "u")
    n = NamespaceID("n")
    fail_add_namespace_user(
        idstorage, None, u, TypeError("namespace_id cannot be None")
    )
    fail_add_namespace_user(idstorage, n, None, TypeError("admin_user cannot be None"))


def test_remove_user_from_namespace_fail_inputs_None(idstorage):
    u = User(AuthsourceID("as"), "u")
    n = NamespaceID("n")
    fail_remove_namespace_user(
        idstorage, None, u, TypeError("namespace_id cannot be None")
    )
    fail_remove_namespace_user(
        idstorage, n, None, TypeError("admin_user cannot be None")
    )


def test_add_user_to_namespace_fail_no_such_namespace(idstorage):
    idstorage.create_namespace(NamespaceID("foo"))
    fail_add_namespace_user(
        idstorage,
        NamespaceID("bar"),
        User(AuthsourceID("as"), Username("u")),
        NoSuchNamespaceError("bar"),
    )


def test_remove_user_from_namespace_fail_no_such_namespace(idstorage):
    idstorage.create_namespace(NamespaceID("foo"))
    idstorage.add_user_to_namespace(
        NamespaceID("foo"), User(AuthsourceID("as"), Username("u"))
    )
    fail_remove_namespace_user(
        idstorage,
        NamespaceID("bar"),
        User(AuthsourceID("as"), Username("u")),
        NoSuchNamespaceError("bar"),
    )


def test_add_user_to_namespace_fail_duplicate(idstorage):
    idstorage.create_namespace(NamespaceID("foo"))
    idstorage.add_user_to_namespace(
        NamespaceID("foo"), User(AuthsourceID("as"), Username("u"))
    )
    fail_add_namespace_user(
        idstorage,
        NamespaceID("foo"),
        User(AuthsourceID("as"), Username("u")),
        UserExistsError("User as/u already administrates namespace foo"),
    )


def test_remove_user_from_namespace_fail_no_such_user(idstorage):
    idstorage.create_namespace(NamespaceID("foo"))
    idstorage.add_user_to_namespace(
        NamespaceID("foo"), User(AuthsourceID("as"), Username("u"))
    )
    fail_remove_namespace_user(
        idstorage,
        NamespaceID("foo"),
        User(AuthsourceID("as"), Username("u1")),
        NoSuchUserError("User as/u1 does not administrate namespace foo"),
    )


def fail_add_namespace_user(idstorage, namespace_id, user, expected):
    with raises(Exception) as got:
        idstorage.add_user_to_namespace(namespace_id, user)
    assert_exception_correct(got.value, expected)


def fail_remove_namespace_user(idstorage, namespace_id, user, expected):
    with raises(Exception) as got:
        idstorage.remove_user_from_namespace(namespace_id, user)
    assert_exception_correct(got.value, expected)


def test_set_namespace_publicly_mappable(idstorage):
    idstorage.create_namespace(NamespaceID("foo"))
    assert idstorage.get_namespace(NamespaceID("foo")) == Namespace(
        NamespaceID("foo"), False
    )

    idstorage.set_namespace_publicly_mappable(NamespaceID("foo"), True)
    assert idstorage.get_namespace(NamespaceID("foo")) == Namespace(
        NamespaceID("foo"), True
    )

    idstorage.set_namespace_publicly_mappable(NamespaceID("foo"), False)
    assert idstorage.get_namespace(NamespaceID("foo")) == Namespace(
        NamespaceID("foo"), False
    )

    idstorage.set_namespace_publicly_mappable(NamespaceID("foo"), True)
    assert idstorage.get_namespace(NamespaceID("foo")) == Namespace(
        NamespaceID("foo"), True
    )

    idstorage.set_namespace_publicly_mappable(NamespaceID("foo"), None)
    assert idstorage.get_namespace(NamespaceID("foo")) == Namespace(
        NamespaceID("foo"), False
    )


def test_set_namespace_publicly_mappable_input_None(idstorage):
    fail_set_namespace_publicly_mappable(
        idstorage, None, TypeError("namespace_id cannot be None")
    )


def test_set_namespace_publicly_mappable_no_such_namespace(idstorage):
    idstorage.create_namespace(NamespaceID("foo"))
    fail_set_namespace_publicly_mappable(
        idstorage, NamespaceID("bar"), NoSuchNamespaceError("bar")
    )


def fail_set_namespace_publicly_mappable(idstorage, namespace_id, expected):
    with raises(Exception) as got:
        idstorage.set_namespace_publicly_mappable(namespace_id, True)
    assert_exception_correct(got.value, expected)


def set_up_data_for_get_namespaces(idstorage):
    idstorage.create_namespace(NamespaceID("ns1"))
    idstorage.set_namespace_publicly_mappable(NamespaceID("ns1"), True)
    idstorage.add_user_to_namespace(
        NamespaceID("ns1"), User(AuthsourceID("as"), Username("u"))
    )

    idstorage.create_namespace(NamespaceID("ns2"))

    idstorage.create_namespace(NamespaceID("ns3"))
    idstorage.add_user_to_namespace(
        NamespaceID("ns3"), User(AuthsourceID("as"), Username("u"))
    )
    idstorage.add_user_to_namespace(
        NamespaceID("ns3"), User(AuthsourceID("astwo"), Username("u3"))
    )

    expected = [
        Namespace(
            NamespaceID("ns1"), True, set([User(AuthsourceID("as"), Username("u"))])
        ),
        Namespace(NamespaceID("ns2"), False),
        Namespace(
            NamespaceID("ns3"),
            False,
            set(
                [
                    User(AuthsourceID("as"), Username("u")),
                    User(AuthsourceID("astwo"), Username("u3")),
                ]
            ),
        ),
    ]
    return expected


def test_get_namespaces(idstorage):
    assert idstorage.get_namespaces() == set()

    expected = set(set_up_data_for_get_namespaces(idstorage))

    assert idstorage.get_namespaces() == expected
    assert idstorage.get_namespaces(None) == expected
    assert idstorage.get_namespaces(nids=None) == expected


def test_get_namespaces_with_nids(idstorage):
    assert idstorage.get_namespaces() == set()

    expected = set_up_data_for_get_namespaces(idstorage)

    assert idstorage.get_namespaces([NamespaceID("ns1")]) == set([expected[0]])
    assert idstorage.get_namespaces(nids=set([NamespaceID("ns1")])) == set(
        [expected[0]]
    )

    nids = {NamespaceID("ns2"), NamespaceID("ns3")}
    assert idstorage.get_namespaces(nids) == set([expected[1], expected[2]])
    assert idstorage.get_namespaces(nids=nids) == set([expected[1], expected[2]])


def test_get_namespaces_fail_None_input(idstorage):
    fail_get_namespaces(
        idstorage, {NamespaceID("foo"), None}, TypeError("None item in nids")
    )


def test_get_namespaces_fail_no_such_namepsace(idstorage):
    idstorage.create_namespace(NamespaceID("foo"))
    fail_get_namespaces(
        idstorage,
        {
            NamespaceID("zoo"),
            NamespaceID("foo"),
            NamespaceID("baz"),
            NamespaceID("aioli_compote_drizzled_on_artisian_tater_tots"),
        },
        NoSuchNamespaceError(
            "['aioli_compote_drizzled_on_artisian_tater_tots', 'baz', 'zoo']"
        ),
    )


def fail_get_namespaces(idstorage, nids, expected):
    with raises(Exception) as got:
        idstorage.get_namespaces(nids)
    assert_exception_correct(got.value, expected)


def test_add_and_get_mapping(idstorage):
    idstorage.add_mapping(
        ObjectID(NamespaceID("foo"), "bar"), ObjectID(NamespaceID("baz"), "bat")
    )
    # add twice to check for no errors or duplictions
    idstorage.add_mapping(
        ObjectID(NamespaceID("foo"), "bar"), ObjectID(NamespaceID("baz"), "bat")
    )

    assert idstorage.find_mappings(ObjectID(NamespaceID("foo"), "bar")) == (
        set([ObjectID(NamespaceID("baz"), "bat")]),
        set(),
    )

    assert idstorage.find_mappings(ObjectID(NamespaceID("baz"), "bat")) == (
        set(),
        set([ObjectID(NamespaceID("foo"), "bar")]),
    )


def test_remove_mapping(idstorage):
    idstorage.add_mapping(
        ObjectID(NamespaceID("foo"), "bar"), ObjectID(NamespaceID("baz"), "bat")
    )
    idstorage.add_mapping(
        ObjectID(NamespaceID("baz"), "bar"), ObjectID(NamespaceID("bar"), "bat")
    )

    # try removing mappings that don't exist
    assert (
        idstorage.remove_mapping(
            ObjectID(NamespaceID("bar"), "bar"), ObjectID(NamespaceID("baz"), "bat")
        )
        is False
    )
    assert (
        idstorage.remove_mapping(
            ObjectID(NamespaceID("foo"), "baz"), ObjectID(NamespaceID("baz"), "bat")
        )
        is False
    )
    assert (
        idstorage.remove_mapping(
            ObjectID(NamespaceID("foo"), "bar"), ObjectID(NamespaceID("bat"), "bat")
        )
        is False
    )
    assert (
        idstorage.remove_mapping(
            ObjectID(NamespaceID("foo"), "bar"), ObjectID(NamespaceID("baz"), "bag")
        )
        is False
    )

    assert idstorage.find_mappings(ObjectID(NamespaceID("foo"), "bar")) == (
        set([ObjectID(NamespaceID("baz"), "bat")]),
        set(),
    )
    assert idstorage.find_mappings(ObjectID(NamespaceID("baz"), "bar")) == (
        set([ObjectID(NamespaceID("bar"), "bat")]),
        set(),
    )

    # remove a mapping that does exist
    assert (
        idstorage.remove_mapping(
            ObjectID(NamespaceID("foo"), "bar"), ObjectID(NamespaceID("baz"), "bat")
        )
        is True
    )

    assert idstorage.find_mappings(ObjectID(NamespaceID("foo"), "bar")) == (
        set(),
        set(),
    )
    assert idstorage.find_mappings(ObjectID(NamespaceID("baz"), "bar")) == (
        set([ObjectID(NamespaceID("bar"), "bat")]),
        set(),
    )

    # try removing the same mapping
    assert (
        idstorage.remove_mapping(
            ObjectID(NamespaceID("foo"), "bar"), ObjectID(NamespaceID("baz"), "bat")
        )
        is False
    )


def test_find_no_mappings(idstorage):
    idstorage.add_mapping(
        ObjectID(NamespaceID("foo"), "bar"), ObjectID(NamespaceID("baz"), "bat")
    )
    idstorage.add_mapping(
        ObjectID(NamespaceID("baz"), "bar"), ObjectID(NamespaceID("bar"), "bat")
    )

    assert idstorage.find_mappings(ObjectID(NamespaceID("bat"), "bar")) == (
        set(),
        set(),
    )
    assert idstorage.find_mappings(ObjectID(NamespaceID("baz"), "bag")) == (
        set(),
        set(),
    )


def test_find_multiple_mappings(idstorage):
    idstorage.add_mapping(
        ObjectID(NamespaceID("foo"), "bar"), ObjectID(NamespaceID("baz"), "bat")
    )
    idstorage.add_mapping(
        ObjectID(NamespaceID("foo"), "bar"), ObjectID(NamespaceID("bar"), "bag")
    )

    idstorage.add_mapping(
        ObjectID(NamespaceID("bag"), "arg"), ObjectID(NamespaceID("foo"), "bar")
    )
    idstorage.add_mapping(
        ObjectID(NamespaceID("bla"), "urg"), ObjectID(NamespaceID("foo"), "bar")
    )

    assert idstorage.find_mappings(ObjectID(NamespaceID("foo"), "bar"), None) == (
        set([ObjectID(NamespaceID("baz"), "bat"), ObjectID(NamespaceID("bar"), "bag")]),
        set([ObjectID(NamespaceID("bag"), "arg"), ObjectID(NamespaceID("bla"), "urg")]),
    )


def test_filter_mappings(idstorage):
    idstorage.add_mapping(
        ObjectID(NamespaceID("foo"), "bar"), ObjectID(NamespaceID("baz"), "bat")
    )
    idstorage.add_mapping(
        ObjectID(NamespaceID("foo"), "bar"), ObjectID(NamespaceID("bar"), "bag")
    )

    idstorage.add_mapping(
        ObjectID(NamespaceID("bag"), "arg"), ObjectID(NamespaceID("foo"), "bar")
    )
    idstorage.add_mapping(
        ObjectID(NamespaceID("bla"), "urg"), ObjectID(NamespaceID("foo"), "bar")
    )

    assert idstorage.find_mappings(
        ObjectID(NamespaceID("foo"), "bar"),
        ns_filter=set([NamespaceID("baz"), NamespaceID("bag")]),
    ) == (
        set([ObjectID(NamespaceID("baz"), "bat")]),
        set([ObjectID(NamespaceID("bag"), "arg")]),
    )


def test_add_mapping_fail_input_None(idstorage):
    oid = ObjectID(NamespaceID("foo"), "bar")
    fail_add_mapping(idstorage, None, oid, TypeError("primary_OID cannot be None"))
    fail_add_mapping(idstorage, oid, None, TypeError("secondary_OID cannot be None"))


def fail_add_mapping(idstorage, pOID, sOID, expected):
    with raises(Exception) as got:
        idstorage.add_mapping(pOID, sOID)
    assert_exception_correct(got.value, expected)


def test_remove_mapping_fail_input_None(idstorage):
    oid = ObjectID(NamespaceID("foo"), "bar")
    fail_remove_mapping(idstorage, None, oid, TypeError("primary_OID cannot be None"))
    fail_remove_mapping(idstorage, oid, None, TypeError("secondary_OID cannot be None"))


def fail_remove_mapping(idstorage, pOID, sOID, expected):
    with raises(Exception) as got:
        idstorage.remove_mapping(pOID, sOID)
    assert_exception_correct(got.value, expected)


def test_find_mappings_fail_input_None(idstorage):
    oid = ObjectID(NamespaceID("foo"), "bar")
    f = set([NamespaceID("foo")])
    fail_find_mappings(idstorage, None, f, TypeError("oid cannot be None"))
    fail_find_mappings(
        idstorage,
        oid,
        set([NamespaceID("foo"), None]),
        TypeError("None item in ns_filter"),
    )


def fail_find_mappings(idstorage, oid, ns_filter, expected):
    with raises(Exception) as got:
        idstorage.find_mappings(oid, ns_filter)
    assert_exception_correct(got.value, expected)
