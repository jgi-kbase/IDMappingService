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
from jgikbase.test.idmapping.test_utils import assert_ms_epoch_close_to_now

DB_NAME = 'test_db_idmapping_service_integration'


def create_deploy_cfg(mongo_port):
    cfg = ConfigParser()
    cfg.add_section('idmapping')
    cfg['idmapping']['mongo-host'] = 'localhost:' + str(mongo_port)
    cfg['idmapping']['mongo-db'] = DB_NAME

    cfg['idmapping']['authentication-enabled'] = 'local, kbase'
    cfg['idmapping']['authentication-admin-enabled'] = 'local, kbase'

    cfg['idmapping']['auth-source-kbase-factory-module'] = (
        'jgikbase.idmapping.userlookup.kbase_user_lookup')
    cfg['idmapping']['auth-source-kbase-init-token'] = 'fake_token_for_mocking'
    cfg['idmapping']['auth-source-kbase-init-url'] = 'http://fake_url_for_mocking.com'
    cfg['idmapping']['auth-source-kbase-init-admin-role'] = 'fake_role_for_mocking'
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
    time.sleep(0.02)
    port = str(portint)
    print('running id mapping service at localhost:' + port)

    yield port

    # shutdown the server
    requests.get('http://localhost:' + port + '/ohgodnothehumanity')


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
