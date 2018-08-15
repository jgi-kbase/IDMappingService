from pytest import fixture
from jgikbase.idmapping.service.mapper_service import create_app
from jgikbase.test.idmapping import test_utils
from jgikbase.test.idmapping.mongo_controller import MongoController
from threading import Thread
from flask import request
from configparser import ConfigParser
import os
import tempfile
import shutil
import requests_mock
import requests
import logging
import time
import re
from jgikbase.test.idmapping.test_utils import assert_ms_epoch_close_to_now,\
    assert_json_error_correct
from pymongo.mongo_client import MongoClient
from jgikbase.idmapping.storage.mongo.id_mapping_mongo_storage import IDMappingMongoStorage
from jgikbase.idmapping.core.user import Username
from jgikbase.idmapping.core.tokens import Token
from jgikbase.idmapping.core.object_id import NamespaceID

# These tests check that all the parts of the system play nice together. That generally means,
# per endpoint, one happy path test and one unhappy path test, where the unhappy path goes
# through as much of the stack as possible.
# The unit tests are responsible for really getting into the nooks and crannies of each class.


DB_NAME = 'test_db_idmapping_service_integration'

KBASE_URL = 'http://fake_url_for_mocking.com'
KBASE_ADMIN_ROLE = 'fake_role_for_mocking'
KBASE_TOKEN = 'fake_token_for_mocking'


def create_deploy_cfg(mongo_port):
    cfg = ConfigParser()
    cfg.add_section('idmapping')
    cfg['idmapping']['mongo-host'] = 'localhost:' + str(mongo_port)
    cfg['idmapping']['mongo-db'] = DB_NAME

    cfg['idmapping']['authentication-enabled'] = 'local, kbase'
    cfg['idmapping']['authentication-admin-enabled'] = 'local, kbase'

    cfg['idmapping']['auth-source-kbase-factory-module'] = (
        'jgikbase.idmapping.userlookup.kbase_user_lookup')
    cfg['idmapping']['auth-source-kbase-init-token'] = KBASE_TOKEN
    cfg['idmapping']['auth-source-kbase-init-url'] = KBASE_URL
    cfg['idmapping']['auth-source-kbase-init-admin-role'] = KBASE_ADMIN_ROLE
    _, path = tempfile.mkstemp('.cfg', 'deploy-', dir=test_utils.get_temp_dir(), text=True)

    with open(path, 'w') as handle:
        cfg.write(handle)

    return path


@fixture(scope='module')
def mongo():
    # remove any current handlers, since tests run in one process
    logging.getLogger().handlers.clear()

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
    if del_temp:
        shutil.rmtree(test_utils.get_temp_dir())


@fixture
def service_port(mongo):
    mongo.clear_database(DB_NAME, drop_indexes=True)

    os.environ['ID_MAPPING_CONFIG'] = create_deploy_cfg(mongo.port)

    with requests_mock.Mocker() as m:
        m.get('http://fake_url_for_mocking.com/',
              request_headers={'Accept': 'application/json'},
              json={'version': '0.1.2', 'gitcommithash': 'hashyhash', 'servertime': 3})
        app = create_app()

    # this is probably the dumbest thing I've ever seen
    @app.route('/ohgodnothehumanity')
    def kill():
        request.environ.get('werkzeug.server.shutdown')()
        return ('', 200)

    portint = test_utils.find_free_port()

    Thread(target=app.run, kwargs={'port': portint}).start()
    time.sleep(0.05)
    port = str(portint)
    print('running id mapping service at localhost:' + port)

    yield port

    # shutdown the server
    requests.get('http://localhost:' + port + '/ohgodnothehumanity')


def get_mongo_storage_instance(mongo):
    client = MongoClient('localhost:' + str(mongo.port))
    return IDMappingMongoStorage(client[DB_NAME])


def test_root(service_port):
    r = requests.get('http://localhost:' + service_port)
    j = r.json()

    time_ = j['servertime']
    commit = j['gitcommithash']
    del j['servertime']
    del j['gitcommithash']

    assert j == {'service': 'ID Mapping Service', 'version': '0.1.0-dev1'}
    assert re.match('[a-f\d]{40}', commit) is not None
    assert_ms_epoch_close_to_now(time_)
    assert r.status_code == 200


def test_create_and_get_namespace(service_port, mongo):
    storage = get_mongo_storage_instance(mongo)
    t = Token('foobar')

    # fail to create a namespace
    r = requests.put('http://localhost:' + service_port + '/api/v1/namespace/myns',
                     headers={'Authorization': 'local ' + t.token})

    assert_json_error_correct(
        r.json(),
        {'error': {'httpcode': 401,
                   'httpstatus': 'Unauthorized',
                   'appcode': 10020,
                   'apperror': 'Invalid token',
                   'message': '10020 Invalid token'
                   }
         })
    assert r.status_code == 401

    # succeed at creating a namespace
    storage.create_local_user(Username('user1'), t.get_hashed_token())
    storage.set_local_user_as_admin(Username('user1'), True)

    r = requests.put('http://localhost:' + service_port + '/api/v1/namespace/myns',
                     headers={'Authorization': 'local ' + t.token})

    assert r.status_code == 204

    # get the namespace with a populated user list
    r = requests.get('http://localhost:' + service_port + '/api/v1/namespace/myns',
                     headers={'Authorization': 'local ' + t.token})

    assert r.json() == {'namespace': 'myns', 'publicly_mappable': False, 'users': []}

    assert r.status_code == 200

    # fail getting a namespace
    r = requests.get('http://localhost:' + service_port + '/api/v1/namespace/myns1')

    assert_json_error_correct(
        r.json(),
        {'error': {'httpcode': 404,
                   'httpstatus': 'Not Found',
                   'appcode': 50010,
                   'apperror': 'No such namespace',
                   'message': '50010 No such namespace: myns1'
                   }
         })
    assert r.status_code == 404


def test_add_remove_user(service_port, mongo):
    storage = get_mongo_storage_instance(mongo)

    lut = Token('foobar')

    storage.create_local_user(Username('lu'), lut.get_hashed_token())
    storage.set_local_user_as_admin(Username('lu'), True)
    storage.create_namespace(NamespaceID('myns'))

    # tests integration with all parts of the kbase user handler
    with requests_mock.Mocker(real_http=True) as m:
        m.get(KBASE_URL + '/api/V2/token', request_headers={'Authorization': 'mytoken'},
              json={'user': 'u1', 'expires': 4800, 'cachefor': 5600})

        m.get(KBASE_URL + '/api/V2/me', request_headers={'Authorization': 'mytoken'},
              json={'customroles': [KBASE_ADMIN_ROLE]})

        m.get(KBASE_URL + '/api/V2/users/?list=imauser',
              request_headers={'Authorization': KBASE_TOKEN},
              json={'imauser': 'im totally a user omg'})

        r = requests.put('http://localhost:' + service_port +
                         '/api/v1/namespace/myns/user/kbase/imauser',
                         headers={'Authorization': 'kbase mytoken'})

    assert r.status_code == 204

    r = requests.get('http://localhost:' + service_port + '/api/v1/namespace/myns',
                     headers={'Authorization': 'local ' + lut.token})

    assert r.json() == {'namespace': 'myns',
                        'publicly_mappable': False,
                        'users': ['kbase/imauser']}
