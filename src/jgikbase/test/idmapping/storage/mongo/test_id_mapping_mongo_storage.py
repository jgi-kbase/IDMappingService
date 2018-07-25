from pytest import fail, fixture
from jgikbase.test.idmapping.mongo_controller import MongoController
from jgikbase.test.idmapping import test_utils
from jgikbase.idmapping.storage.mongo.id_mapping_mongo_storage import IDMappingMongoStorage
from jgikbase.idmapping.core.user import User, AuthsourceID, LOCAL
from jgikbase.idmapping.core.tokens import HashedToken
from jgikbase.test.idmapping.test_utils import assert_exception_correct
from pymongo.errors import DuplicateKeyError
from jgikbase.idmapping.core.errors import NoSuchUserError, UserExistsError, InvalidTokenError,\
    NamespaceExistsError, NoSuchNamespaceError
from jgikbase.idmapping.storage.errors import IDMappingStorageError, StorageInitException
import re
from jgikbase.idmapping.core.object_id import NamespaceID, Namespace

TEST_DB_NAME = 'test_id_mapping'


@fixture(scope='module')
def mongo():
    mongoexe = test_utils.get_mongo_exe()
    tempdir = test_utils.get_temp_dir()
    wt = test_utils.get_use_wired_tiger()
    mongo = MongoController(mongoexe, tempdir, wt)
    print('running mongo {}{} on port {} in dir {}'.format(
        mongo.db_version, ' with WiredTiger' if wt else '', mongo.port, mongo.temp_dir))
    yield mongo
    del_temp = test_utils.get_delete_temp_files()
    print('shutting down mongo, delete_temp_files={}'.format(del_temp))
    mongo.destroy(del_temp)


@fixture
def idstorage(mongo):
    mongo.clear_database(TEST_DB_NAME, drop_indexes=True)
    return IDMappingMongoStorage(mongo.client[TEST_DB_NAME])


def test_fail_startup():
    try:
        IDMappingMongoStorage(None)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, TypeError('db cannot be None'))

# The following tests ensure that all indexes are created correctly. The collection names
# are tested so that if a new collection is added the test will fail without altering
# said test, at which time the coder will hopefully read this notice and add index tests
# for the new collection.


def test_collection_names(idstorage, mongo):
    names = mongo.client[TEST_DB_NAME].list_collection_names()
    expected = set(['users', 'config', 'ns'])
    if mongo.includes_system_indexes:
        expected.add('system.indexes')
    assert set(names) == expected


def test_index_config(idstorage, mongo):
    v = mongo.index_version
    indexes = mongo.client[TEST_DB_NAME]['config'].index_information()
    expected = {'_id_': {'v': v, 'key': [('_id', 1)], 'ns': 'test_id_mapping.config'},
                'schema_1': {'v': v, 'unique': True, 'key': [('schema', 1)],
                             'ns': 'test_id_mapping.config'}}
    assert indexes == expected


def test_index_user(idstorage, mongo):
    v = mongo.index_version
    indexes = mongo.client[TEST_DB_NAME]['users'].index_information()
    expected = {'_id_': {'v': v, 'key': [('_id', 1)], 'ns': 'test_id_mapping.users'},
                'user_1': {'v': v, 'unique': True, 'key': [('user', 1)],
                           'ns': 'test_id_mapping.users'},
                'hshtkn_1': {'v': v, 'unique': True, 'key': [('hshtkn', 1)],
                             'ns': 'test_id_mapping.users'}}
    assert indexes == expected


def test_index_namespace(idstorage, mongo):
    v = mongo.index_version
    indexes = mongo.client[TEST_DB_NAME]['ns'].index_information()
    expected = {'_id_': {'v': v, 'key': [('_id', 1)], 'ns': 'test_id_mapping.ns'},
                'nsid_1': {'v': v, 'unique': True, 'key': [('nsid', 1)],
                           'ns': 'test_id_mapping.ns'}}
    assert indexes == expected


def test_startup_and_check_config_doc(idstorage, mongo):
    col = mongo.client[TEST_DB_NAME]['config']
    assert col.count() == 1  # only one config doc
    cfgdoc = col.find_one()
    assert cfgdoc['schema'] == 'schema'
    assert cfgdoc['schemaver'] == 1
    assert cfgdoc['inupdate'] is False

    # check startup works with cfg object in place
    idmap = IDMappingMongoStorage(mongo.client[TEST_DB_NAME])
    idmap.create_local_user(User(LOCAL, 'foo'), HashedToken('t'))
    assert idmap.get_user(HashedToken('t')) == User(LOCAL, 'foo')


def test_startup_with_2_config_docs(mongo):
    col = mongo.client[TEST_DB_NAME]['config']
    col.drop()  # clear db independently of creating a idmapping mongo instance
    col.insert_many([{'schema': 'schema', 'schemaver': 1, 'inupdate': False},
                     {'schema': 'schema', 'schemaver': 2, 'inupdate': False}])

    # pattern matcher for the error format across python 2 & 3
    p = re.compile(
        'Failed to create index: E11000 duplicate key error (index|collection): ' +
        r'test_id_mapping.config( index: |\.\$)schema_1\s+dup key: ' +
        r'\{ : "schema" \}')

    try:
        IDMappingMongoStorage(mongo.client[TEST_DB_NAME])
        fail('expected exception')
    except StorageInitException as e:
        assert p.match(e.args[0]) is not None


def test_startup_with_bad_schema_version(mongo):
    col = mongo.client[TEST_DB_NAME]['config']
    col.drop()  # clear db independently of creating a idmapping mongo instance
    col.insert_one({'schema': 'schema', 'schemaver': 4, 'inupdate': False})

    try:
        IDMappingMongoStorage(mongo.client[TEST_DB_NAME])
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, StorageInitException(
            'Incompatible database schema. Server is v1, DB is v4'))


def test_startup_in_update(mongo):
    col = mongo.client[TEST_DB_NAME]['config']
    col.drop()  # clear db independently of creating a idmapping mongo instance
    col.insert_one({'schema': 'schema', 'schemaver': 1, 'inupdate': True})

    try:
        IDMappingMongoStorage(mongo.client[TEST_DB_NAME])
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, StorageInitException(
            'The database is in the middle of an update from v1 of the ' +
            'schema. Aborting startup.'))


def test_create_update_and_get_user(idstorage):
    # create
    idstorage.create_local_user(User(AuthsourceID('local'), 'foo'), HashedToken('bar'))
    u = idstorage.get_user(HashedToken('bar'))
    assert u.username == 'foo'
    assert u.authsource_id == LOCAL

    # update
    idstorage.update_local_user(User(AuthsourceID('local'), 'foo'), HashedToken('bat'))
    u = idstorage.get_user(HashedToken('bat'))
    assert u.username == 'foo'
    assert u.authsource_id == LOCAL

    idstorage.update_local_user(User(AuthsourceID('local'), 'foo'), HashedToken('boo'))
    u = idstorage.get_user(HashedToken('boo'))
    assert u.username == 'foo'
    assert u.authsource_id == LOCAL

    # test different user
    idstorage.create_local_user(User(AuthsourceID('local'), 'foo1'), HashedToken('baz'))
    u = idstorage.get_user(HashedToken('baz'))
    assert u.username == 'foo1'
    assert u.authsource_id == LOCAL


def test_create_user_fail_input_None(idstorage):
    t = HashedToken('t')
    u = User(LOCAL, 'u')
    fail_create_user(idstorage, None, t, TypeError('user cannot be None'))
    fail_create_user(idstorage, u, None, TypeError('token cannot be None'))


def test_create_user_fail_not_local(idstorage):
    u = User(AuthsourceID('a'), 'u')
    t = HashedToken('t')
    fail_create_user(idstorage, u, t, ValueError('Only users from a local authsource are allowed'))


def test_create_user_fail_duplicate_user(idstorage):
    idstorage.create_local_user(User(LOCAL, 'u'), HashedToken('t'))
    fail_create_user(idstorage, User(LOCAL, 'u'), HashedToken('t1'), UserExistsError('u'))


def test_create_user_fail_duplicate_token(idstorage):
    idstorage.create_local_user(User(LOCAL, 'u'), HashedToken('t'))
    fail_create_user(idstorage, User(LOCAL, 'u1'), HashedToken('t'),
                     ValueError('The provided token already exists in the database'))


def fail_create_user(idstorage, user, token, expected):
    try:
        idstorage.create_local_user(user, token)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)


def test_update_user_fail_input_None(idstorage):
    t = HashedToken('t')
    u = User(LOCAL, 'u')
    fail_update_user(idstorage, None, t, TypeError('user cannot be None'))
    fail_update_user(idstorage, u, None, TypeError('token cannot be None'))


def test_update_user_fail_not_local(idstorage):
    u = User(AuthsourceID('a'), 'u')
    t = HashedToken('t')
    fail_update_user(idstorage, u, t, ValueError('Only users from a local authsource are allowed'))


def test_update_user_fail_duplicate_token(idstorage):
    idstorage.create_local_user(User(LOCAL, 'u'), HashedToken('t'))
    idstorage.create_local_user(User(LOCAL, 'u1'), HashedToken('t1'))
    fail_update_user(idstorage, User(LOCAL, 'u1'), HashedToken('t'),
                     ValueError('The provided token already exists in the database'))


def test_update_user_fail_no_such_user(idstorage):
    idstorage.create_local_user(User(LOCAL, 'u'), HashedToken('t'))
    fail_update_user(idstorage, User(LOCAL, 'u1'), HashedToken('t1'),
                     NoSuchUserError('u1'))


def fail_update_user(idstorage, user, token, expected):
    try:
        idstorage.update_local_user(user, token)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)


def test_get_user_fail_input_None(idstorage):
    fail_get_user(idstorage, None, TypeError('token cannot be None'))


def test_get_user_fail_no_such_token(idstorage):
    idstorage.create_local_user(User(LOCAL, 'u'), HashedToken('t'))
    fail_get_user(idstorage, HashedToken('t1'), InvalidTokenError())


def fail_get_user(idstorage, token, expected):
    try:
        idstorage.get_user(token)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)


def test_unparseable_duplicate_key_exception(idstorage):
    # this is a very naughty test reaching into the implementation
    try:
        idstorage._get_duplicate_location(DuplicateKeyError('unmatchable dup key foo'))
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(
            got, IDMappingStorageError('unable to parse duplicate key error: unmatchable '))


def test_get_users(idstorage):
    assert idstorage.get_users() == set()

    idstorage.create_local_user(User(LOCAL, 'foo'), HashedToken('t1'))

    assert idstorage.get_users() == {User(LOCAL, 'foo')}

    idstorage.create_local_user(User(LOCAL, 'mrsentity'), HashedToken('t2'))
    idstorage.create_local_user(User(LOCAL, 'mrsenigma'), HashedToken('t3'))
    idstorage.update_local_user(User(LOCAL, 'mrsenigma'), HashedToken('t4'))

    assert idstorage.get_users() == {User(LOCAL, 'foo'), User(LOCAL, 'mrsenigma'),
                                     User(LOCAL, 'mrsentity')}


def test_create_and_get_namespace(idstorage):
    idstorage.create_namespace(NamespaceID('foo'))
    expected = Namespace(NamespaceID('foo'), False, None)

    assert idstorage.get_namespace(NamespaceID('foo')) == expected

    idstorage.create_namespace(NamespaceID('bar'))
    expected = Namespace(NamespaceID('bar'), False, None)

    assert idstorage.get_namespace(NamespaceID('bar')) == expected


def test_create_namespace_fail_input_None(idstorage):
    fail_create_namespace(idstorage, None, TypeError('namespace_id cannot be None'))


def test_create_namespace_fail_namespace_exists(idstorage):
    idstorage.create_namespace(NamespaceID('foo'))

    fail_create_namespace(idstorage, NamespaceID('foo'), NamespaceExistsError('foo'))


def fail_create_namespace(idstorage, namespace_id, expected):
    try:
        idstorage.create_namespace(namespace_id)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)


def test_get_namespace_fail_input_None(idstorage):
    fail_get_namespace(idstorage, None, TypeError('namespace_id cannot be None'))


def test_get_namespace_fail_no_such_namespace(idstorage):
    idstorage.create_namespace(NamespaceID('foo'))
    fail_get_namespace(idstorage, NamespaceID('bar'), NoSuchNamespaceError('bar'))


def fail_get_namespace(idstorage, namespace_id, expected):
    try:
        idstorage.get_namespace(namespace_id)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)


def test_add_and_remove_namespace_users(idstorage):
    nsid = NamespaceID('foo')
    idstorage.create_namespace(nsid)
    assert idstorage.get_namespace(NamespaceID('foo')) == Namespace(NamespaceID('foo'), False)

    idstorage.add_user_to_namespace(nsid, User(AuthsourceID('asone'), 'u1'))
    users = set([User(AuthsourceID('asone'), 'u1')])
    assert idstorage.get_namespace(nsid) == Namespace(NamespaceID('foo'), False, users)

    idstorage.add_user_to_namespace(nsid, User(AuthsourceID('astwo'), 'u2'))
    users.add(User(AuthsourceID('astwo'), 'u2'))
    assert idstorage.get_namespace(nsid) == Namespace(NamespaceID('foo'), False, users)

    idstorage.remove_user_from_namespace(NamespaceID('foo'), User(AuthsourceID('asone'), 'u1'))
    users = set([User(AuthsourceID('astwo'), 'u2')])
    assert idstorage.get_namespace(nsid) == Namespace(NamespaceID('foo'), False, users)

    idstorage.remove_user_from_namespace(NamespaceID('foo'), User(AuthsourceID('astwo'), 'u2'))
    assert idstorage.get_namespace(nsid) == Namespace(NamespaceID('foo'), False)


def test_add_user_to_namespace_fail_inputs_None(idstorage):
    u = User(LOCAL, 'u')
    n = NamespaceID('n')
    fail_add_namespace_user(idstorage, None, u, TypeError('namespace_id cannot be None'))
    fail_add_namespace_user(idstorage, n, None, TypeError('admin_user cannot be None'))


def test_remove_user_from_namespace_fail_inputs_None(idstorage):
    u = User(LOCAL, 'u')
    n = NamespaceID('n')
    fail_remove_namespace_user(idstorage, None, u, TypeError('namespace_id cannot be None'))
    fail_remove_namespace_user(idstorage, n, None, TypeError('admin_user cannot be None'))


def test_add_user_to_namespace_fail_no_such_namespace(idstorage):
    idstorage.create_namespace(NamespaceID('foo'))
    fail_add_namespace_user(idstorage, NamespaceID('bar'), User(LOCAL, 'u'),
                            NoSuchNamespaceError('bar'))


def test_remove_user_from_namespace_fail_no_such_namespace(idstorage):
    idstorage.create_namespace(NamespaceID('foo'))
    idstorage.add_user_to_namespace(NamespaceID('foo'), User(LOCAL, 'u'))
    fail_remove_namespace_user(idstorage, NamespaceID('bar'), User(LOCAL, 'u'),
                               NoSuchNamespaceError('bar'))


def test_add_user_to_namespace_fail_duplicate(idstorage):
    idstorage.create_namespace(NamespaceID('foo'))
    idstorage.add_user_to_namespace(NamespaceID('foo'), User(LOCAL, 'u'))
    fail_add_namespace_user(idstorage, NamespaceID('foo'), User(LOCAL, 'u'),
                            UserExistsError('User local/u already administrates namespace foo'))


def test_remove_user_from_namespace_fail_no_such_user(idstorage):
    idstorage.create_namespace(NamespaceID('foo'))
    idstorage.add_user_to_namespace(NamespaceID('foo'), User(LOCAL, 'u'))
    fail_remove_namespace_user(
        idstorage, NamespaceID('foo'), User(LOCAL, 'u1'),
        NoSuchUserError('User local/u1 does not administrate namespace foo'))


def fail_add_namespace_user(idstorage, namespace_id, user, expected):
    try:
        idstorage.add_user_to_namespace(namespace_id, user)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)


def fail_remove_namespace_user(idstorage, namespace_id, user, expected):
    try:
        idstorage.remove_user_from_namespace(namespace_id, user)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)


def test_set_namespace_publicly_mappable(idstorage):
    idstorage.create_namespace(NamespaceID('foo'))
    assert idstorage.get_namespace(NamespaceID('foo')) == Namespace(NamespaceID('foo'), False)

    idstorage.set_namespace_publicly_mappable(NamespaceID('foo'), True)
    assert idstorage.get_namespace(NamespaceID('foo')) == Namespace(NamespaceID('foo'), True)

    idstorage.set_namespace_publicly_mappable(NamespaceID('foo'), False)
    assert idstorage.get_namespace(NamespaceID('foo')) == Namespace(NamespaceID('foo'), False)

    idstorage.set_namespace_publicly_mappable(NamespaceID('foo'), True)
    assert idstorage.get_namespace(NamespaceID('foo')) == Namespace(NamespaceID('foo'), True)

    idstorage.set_namespace_publicly_mappable(NamespaceID('foo'), None)
    assert idstorage.get_namespace(NamespaceID('foo')) == Namespace(NamespaceID('foo'), False)


def test_set_namespace_publicly_mappable_input_None(idstorage):
    fail_set_namespace_publicly_mappable(idstorage, None, TypeError('namespace_id cannot be None'))


def test_set_namespace_publibly_mappable_no_such_namespace(idstorage):
    idstorage.create_namespace(NamespaceID('foo'))
    fail_set_namespace_publicly_mappable(idstorage, NamespaceID('bar'),
                                         NoSuchNamespaceError('bar'))


def fail_set_namespace_publicly_mappable(idstorage, namespace_id, expected):
    try:
        idstorage.set_namespace_publicly_mappable(namespace_id, True)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)


def test_get_namespaces(idstorage):
    assert idstorage.get_namespaces() == set()

    idstorage.create_namespace(NamespaceID('ns1'))
    idstorage.set_namespace_publicly_mappable(NamespaceID('ns1'), True)
    idstorage.add_user_to_namespace(NamespaceID('ns1'), User(AuthsourceID('as'), 'u'))

    idstorage.create_namespace(NamespaceID('ns2'))

    idstorage.create_namespace(NamespaceID('ns3'))
    idstorage.add_user_to_namespace(NamespaceID('ns3'), User(AuthsourceID('as'), 'u'))
    idstorage.add_user_to_namespace(NamespaceID('ns3'), User(AuthsourceID('astwo'), 'u3'))

    assert idstorage.get_namespaces() == \
        {Namespace(NamespaceID('ns1'), True, set([User(AuthsourceID('as'), 'u')])),
         Namespace(NamespaceID('ns2'), False),
         Namespace(NamespaceID('ns3'), False, set([User(AuthsourceID('as'), 'u'),
                                                   User(AuthsourceID('astwo'), 'u3')]))}
