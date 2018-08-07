from unittest.mock import create_autospec, MagicMock
from pathlib import Path
from jgikbase.idmapping.config import KBaseConfig, IDMappingConfigError
import os
from pytest import raises
from jgikbase.test.idmapping.test_utils import assert_exception_correct
from jgikbase.idmapping.core.user import AuthsourceID


def mock_file(path, contents):
    # tried autospeccing io.FileIO, but get attribute error for name, even though it's doc'd
    # probably set in constructor
    f = MagicMock()
    f.name = path
    f.__enter__.return_value = f
    f.__iter__.return_value = contents
    return f


def mock_path_to_file(path, contents, is_file=True) -> Path:
    p = create_autospec(Path, spec_set=True, instance=True)
    p.__str__.return_value = path
    p.is_file.return_value = is_file
    p.open.return_value = mock_file(path, contents)
    return p


def test_kb_config_get_env():
    # to avoid dealing with files in the tests, we reach into the implementation here a little bit
    p = mock_path_to_file('path/place', ['[idmapping]', 'mongo-host=foo', 'mongo-db=bar'])
    c = KBaseConfig(p)

    os.environ['ID_MAPPING_CONFIG'] = 'some/path'
    os.environ['KB_DEPLOYMENT_CONFIG'] = 'some/other/path'

    assert c._get_cfg_from_env() == Path('some/path')

    del os.environ['ID_MAPPING_CONFIG']

    assert c._get_cfg_from_env() == Path('some/other/path')

    del os.environ['KB_DEPLOYMENT_CONFIG']

    with raises(Exception) as got:
        c._get_cfg_from_env()
    assert_exception_correct(got.value, IDMappingConfigError(
        'Could not find deployment configuration file from either permitted environment ' +
        'variable: ID_MAPPING_CONFIG, KB_DEPLOYMENT_CONFIG'))


def test_kb_config_minimal_config():
    p = mock_path_to_file('path', ['[idmapping]', 'mongo-host=foo', 'mongo-db=bar'])
    c = KBaseConfig(p)

    assert c.mongo_host == 'foo'
    assert c.mongo_db == 'bar'
    assert c.mongo_user is None
    assert c.mongo_pwd is None
    assert c.auth_enabled == set()
    assert c.auth_admin_enabled == set()
    assert c.ignore_ip_headers is False


def test_kb_config_minimal_config_whitespace():
    p = mock_path_to_file('path', ['[idmapping]',
                                   'mongo-host=foo', 'mongo-db=bar',
                                   'mongo-user=  \t   ', 'mongo-pwd=  \t   ',
                                   'dont-trust-x-ip-headers=   crap',
                                   'authentication-enabled=    \t     ',
                                   'authentication-admin-enabled=      \t     '])
    c = KBaseConfig(p)

    assert c.mongo_host == 'foo'
    assert c.mongo_db == 'bar'
    assert c.mongo_user is None
    assert c.mongo_pwd is None
    assert c.auth_enabled == set()
    assert c.auth_admin_enabled == set()
    assert c.ignore_ip_headers is False


def test_kb_config_maximal_config():
    p = mock_path_to_file('path', [
        '[idmapping]', 'mongo-host=foo', 'mongo-db=bar', 'mongo-user=u', 'mongo-pwd=p',
        'dont-trust-x-ip-headers=true',
        'authentication-enabled=   authone,   auththree, \t  authtwo  , local ',
        'authentication-admin-enabled=   authone,   autha, \t  authbcd   ',
        'auth-source-authone-factory-module=  some.module  \t  ',
        'auth-source-authtwo-factory-module=   some.other.module    \t ',
        'auth-source-authtwo-init-key=  val    \t  ',
        'auth-source-authtwo-init-whee=  whoo    \t  ',
        'auth-source-auththree-factory-module=   some.other.other.module    \t ',
        'auth-source-auththree-init-x=Y'])
    c = KBaseConfig(p)

    assert c.mongo_host == 'foo'
    assert c.mongo_db == 'bar'
    assert c.mongo_user == 'u'
    assert c.mongo_pwd == 'p'
    assert c.auth_enabled == set([AuthsourceID('authone'), AuthsourceID('authtwo'),
                                  AuthsourceID('auththree'), AuthsourceID('local')])
    assert c.auth_admin_enabled == set([AuthsourceID('authone'), AuthsourceID('authbcd'),
                                        AuthsourceID('autha')])
    assert c.lookup_configs == {AuthsourceID('authone'): ('some.module', {}),
                                AuthsourceID('authtwo'): ('some.other.module', {'key': 'val',
                                                                                'whee': 'whoo'}),
                                AuthsourceID('auththree'): ('some.other.other.module', {'x': 'Y'})}
    assert c.ignore_ip_headers is True


def test_kb_config_fail_not_file():
    fail_kb_config(mock_path_to_file('path/2/whee', [], False), IDMappingConfigError(
        'path/2/whee does not exist or is not a file'))


def test_kb_config_fail_corrupt():
    # only test one of the many ways a file can be corrupt per configparser
    fail_kb_config(mock_path_to_file('path/2/whee', ['whee'], True), IDMappingConfigError(
        'Error parsing config file path/2/whee: File contains no section headers.\n' +
        "file: 'path/2/whee', line: 1\n" +
        "'whee'"))


def test_kb_config_fail_no_section():
    fail_kb_config(mock_path_to_file('path/2/whee', ['[sec]'], True), IDMappingConfigError(
        'No section idmapping found in config file path/2/whee'))


def test_kb_config_fail_no_mongo_host():
    err = ('Required parameter mongo-host not provided in configuration file path/2/whee, ' +
           'section idmapping')
    contents = ['[idmapping]', 'mongo-db=foo']
    fail_kb_config(mock_path_to_file('path/2/whee', contents, True), IDMappingConfigError(err))

    contents = ['[idmapping]', 'mongo-host=  \t   ', 'mongo-db=foo']
    fail_kb_config(mock_path_to_file('path/2/whee', contents, True), IDMappingConfigError(err))


def test_kb_config_fail_no_mongo_db():
    err = ('Required parameter mongo-db not provided in configuration file path/2/whee, ' +
           'section idmapping')
    contents = ['[idmapping]', 'mongo-host=foo']
    fail_kb_config(mock_path_to_file('path/2/whee', contents, True), IDMappingConfigError(err))

    contents = ['[idmapping]', 'mongo-db=  \t   ', 'mongo-host=foo']
    fail_kb_config(mock_path_to_file('path/2/whee', contents, True), IDMappingConfigError(err))


def test_kb_config_fail_user_no_pwd():
    err = ('Must provide both mongo-user and mongo-pwd params in config file path/2/whee ' +
           'section idmapping if MongoDB authentication is to be used')
    contents = ['[idmapping]', 'mongo-host=foo', 'mongo-db=bar', 'mongo-user=foo']
    fail_kb_config(mock_path_to_file('path/2/whee', contents, True), IDMappingConfigError(err))

    contents = ['[idmapping]', 'mongo-host=foo', 'mongo-db=bar', 'mongo-user=foo',
                'mongo-pwd=  \t   ']
    fail_kb_config(mock_path_to_file('path/2/whee', contents, True), IDMappingConfigError(err))


def test_kb_config_fail_pwd_no_user():
    err = ('Must provide both mongo-user and mongo-pwd params in config file path/2/whee ' +
           'section idmapping if MongoDB authentication is to be used')
    contents = ['[idmapping]', 'mongo-host=foo', 'mongo-db=bar', 'mongo-pwd=foo']
    fail_kb_config(mock_path_to_file('path/2/whee', contents, True), IDMappingConfigError(err))

    contents = ['[idmapping]', 'mongo-host=foo', 'mongo-db=bar', 'mongo-pwd=foo',
                'mongo-user=  \t   ']
    fail_kb_config(mock_path_to_file('path/2/whee', contents, True), IDMappingConfigError(err))


def test_kb_config_fail_illegal_authsource():
    err = ('Parameter authentication-enabled in configuration file path/2/whee, ' +
           'section idmapping, is invalid: 30001 Illegal input parameter: Illegal character ' +
           'in authsource id bleah1: 1')
    contents = ['[idmapping]', 'mongo-host=foo', 'mongo-db=bar',
                'authentication-enabled= foo,   bar,   bleah1, yay']
    fail_kb_config(mock_path_to_file('path/2/whee', contents, True), IDMappingConfigError(err))

    err = ('Parameter authentication-enabled in configuration file path/2/whee, ' +
           'section idmapping, has whitespace-only entry')
    contents = ['[idmapping]', 'mongo-host=foo', 'mongo-db=bar',
                'authentication-enabled= foo,   bar,  , bleah, yay']
    fail_kb_config(mock_path_to_file('path/2/whee', contents, True), IDMappingConfigError(err))


def test_kb_config_fail_illegal_authsource_admin():
    err = ('Parameter authentication-admin-enabled in configuration file path/2/whee, ' +
           'section idmapping, is invalid: 30001 Illegal input parameter: Illegal character ' +
           'in authsource id bleach1: 1')
    contents = ['[idmapping]', 'mongo-host=foo', 'mongo-db=bar',
                'authentication-admin-enabled= foo,   bar,   bleach1, yay']
    fail_kb_config(mock_path_to_file('path/2/whee', contents, True), IDMappingConfigError(err))

    err = ('Parameter authentication-admin-enabled in configuration file path/2/whee, ' +
           'section idmapping, has whitespace-only entry')
    contents = ['[idmapping]', 'mongo-host=foo', 'mongo-db=bar',
                'authentication-admin-enabled= foo,   bar,  , bleah, yay']
    fail_kb_config(mock_path_to_file('path/2/whee', contents, True), IDMappingConfigError(err))


def test_kb_config_fail_auth_source_unexpected_key():
    err = ('Unexpected parameter auth-source-foo-boratrulez in configuration file path/2/whee, ' +
           'section idmapping')
    contents = ['[idmapping]', 'mongo-host=foo', 'mongo-db=bar',
                'authentication-enabled= foo',
                'auth-source-foo-boratrulez= yes. yes he does']
    fail_kb_config(mock_path_to_file('path/2/whee', contents, True), IDMappingConfigError(err))


def test_kb_config_fail_auth_source_missing_factory():
    err = ('Required parameter auth-source-foo-factory-module not provided in ' +
           'configuration file path/2/whee, section idmapping')
    contents = ['[idmapping]', 'mongo-host=foo', 'mongo-db=bar',
                'authentication-enabled= foo',
                'auth-source-foo-init-borat= yes. yes he does']
    fail_kb_config(mock_path_to_file('path/2/whee', contents, True), IDMappingConfigError(err))

    contents = ['[idmapping]', 'mongo-host=foo', 'mongo-db=bar',
                'authentication-enabled= foo',
                'auth-source-foo-init-borat= yes. yes he does'
                'auth-source-foo-factory-module=    \t    ']
    fail_kb_config(mock_path_to_file('path/2/whee', contents, True), IDMappingConfigError(err))


def fail_kb_config(path: Path, expected: Exception):
    with raises(Exception) as got:
        KBaseConfig(path)
    assert_exception_correct(got.value, expected)
