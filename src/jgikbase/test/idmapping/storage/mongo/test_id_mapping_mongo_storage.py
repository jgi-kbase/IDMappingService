from pytest import fixture
from jgikbase.test.idmapping.mongo_controller import MongoController
from jgikbase.test.idmapping import test_utils
from jgikbase.idmapping.storage.mongo.id_mapping_mongo_storage import IDMappingMongoStorage
from jgikbase.idmapping.core.user import User, AuthsourceID
from jgikbase.idmapping.core.tokens import HashedToken

TEST_DB_NAME = 'test_id_mapping'


@fixture(scope='module')
def mongo():
    mongoexe = test_utils.get_mongo_exe()
    tempdir = test_utils.get_temp_dir()
    wt = test_utils.get_use_wired_tiger()
    mongo = MongoController(mongoexe, tempdir, wt)
    print('running mongo {} on port {} in dir {}'.format(
        mongo.db_version, mongo.port, mongo.temp_dir))
    yield mongo
    del_temp = test_utils.get_delete_temp_files()
    print('shutting down mongo, delete_temp_files={}'.format(del_temp))
    mongo.destroy(del_temp)


@fixture
def idstorage(mongo):
    mongo.clear_database(TEST_DB_NAME, drop_indexes=True)
    return IDMappingMongoStorage(mongo.client[TEST_DB_NAME])


def test_save_and_get_user(idstorage):
    idstorage.create_or_update_local_user(User(AuthsourceID('as'), 'foo'), HashedToken('bar'))
    u = idstorage.get_user(HashedToken('bar'))
    assert u.username == 'foo'
    assert u.authsource.authsource == 'as'
