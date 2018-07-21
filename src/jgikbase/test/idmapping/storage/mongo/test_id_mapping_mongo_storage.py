from pytest import fail, fixture
from jgikbase.test.idmapping.mongo_controller import MongoController
from jgikbase.test.idmapping import test_utils
from jgikbase.idmapping.storage.mongo.id_mapping_mongo_storage import IDMappingMongoStorage
from jgikbase.idmapping.core.user import User, AuthsourceID
from jgikbase.idmapping.core.tokens import HashedToken
from jgikbase.test.idmapping.test_utils import assert_exception_correct

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
                'auth_1_user_1': {'v': v, 'unique': True, 'key': [('auth', 1), ('user', 1)],
                                  'ns': 'test_id_mapping.users'},
                'hshtkn_1': {'v': v, 'unique': True, 'key': [('hshtkn', 1)],
                             'ns': 'test_id_mapping.users'}}
    assert indexes == expected


def test_save_and_get_user(idstorage):
    idstorage.create_or_update_local_user(User(AuthsourceID('as'), 'foo'), HashedToken('bar'))
    u = idstorage.get_user(HashedToken('bar'))
    assert u.username == 'foo'
    assert u.authsource.authsource == 'as'
