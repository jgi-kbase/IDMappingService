from pytest import fail, fixture
from jgikbase.test.idmapping.mongo_controller import MongoController
from jgikbase.test.idmapping import test_utils
from jgikbase.idmapping.storage.mongo.id_mapping_mongo_storage import IDMappingMongoStorage
from jgikbase.idmapping.core.user import User, AuthsourceID, LOCAL
from jgikbase.idmapping.core.tokens import HashedToken
from jgikbase.test.idmapping.test_utils import assert_exception_correct
from pymongo.errors import DuplicateKeyError
from jgikbase.idmapping.core.errors import NoSuchUserError, UserExistsError, InvalidTokenError
from jgikbase.idmapping.storage.errors import IDMappingStorageError

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
        assert_exception_correct(got, ValueError('db cannot be None'))

# The following tests ensure that all indexes are created correctly. The collection names
# are tested so that if a new collection is added the test will fail without altering
# said test, at which time the coder will hopefully read this notice and add index tests
# for the new collection.


def test_collection_names(idstorage, mongo):
    names = mongo.client[TEST_DB_NAME].list_collection_names()
    expected = ['users']
    if mongo.includes_system_indexes:
        expected.append('system.indexes')
    assert names == expected


def test_index_user(idstorage, mongo):
    indexes = mongo.client[TEST_DB_NAME]['users'].index_information()
    v = mongo.index_version
    expected = {'_id_': {'v': v, 'key': [('_id', 1)], 'ns': 'test_id_mapping.users'},
                'user_1': {'v': v, 'unique': True, 'key': [('user', 1)],
                           'ns': 'test_id_mapping.users'},
                'hshtkn_1': {'v': v, 'unique': True, 'key': [('hshtkn', 1)],
                             'ns': 'test_id_mapping.users'}}
    assert indexes == expected


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
    fail_create_user(idstorage, None, t, ValueError('user cannot be None'))
    fail_create_user(idstorage, u, None, ValueError('token cannot be None'))


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
    fail_update_user(idstorage, None, t, ValueError('user cannot be None'))
    fail_update_user(idstorage, u, None, ValueError('token cannot be None'))


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
    fail_get_user(idstorage, None, ValueError('token cannot be None'))


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
