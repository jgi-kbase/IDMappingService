from jgikbase.idmapping.userlookup.kbase_user_lookup import KBaseUserLookup, build_lookup
from jgikbase.idmapping.core.user import AuthsourceID, User, Username
from jgikbase.idmapping.core.tokens import Token
import requests_mock
from pytest import raises
from jgikbase.test.idmapping.test_utils import assert_exception_correct, TerstFermerttr
from jgikbase.idmapping.core.errors import InvalidTokenError
import copy
from jgikbase.idmapping.core.user_lookup import LookupInitializationError
from pytest import fixture
from logging import StreamHandler
import logging


@fixture(scope='module')
def init_logger():
    print('log collector init')
    handler = StreamHandler()
    formatter = TerstFermerttr()
    handler.setFormatter(formatter)
    # remove any current handlers, since tests run in one process
    logging.getLogger().handlers.clear()
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel('INFO')
    return formatter.logs


@fixture
def log_collector(init_logger):
    print('clearing logs')
    init_logger.clear()
    return init_logger


def assert_logs_correct(logs, logstring):
    assert len(logs) == 1
    logrecord = logs[0]
    assert logrecord.name == 'jgikbase.idmapping.userlookup.kbase_user_lookup'
    assert logrecord.levelname == 'INFO'
    assert logrecord.getMessage() == logstring


def test_init():
    with requests_mock.Mocker() as m:
        m.get('http://whee.com/',
              request_headers={'Accept': 'application/json'},
              json={'version': '0.1.2', 'gitcommithash': 'hashyhash', 'servertime': 3})
        kbuh = KBaseUserLookup('http://whee.com', Token('foo'), 'admin')
        assert kbuh.auth_url == 'http://whee.com/'


def test_init_with_builder():
    with requests_mock.Mocker() as m:
        m.get('http://whee.com/',
              request_headers={'Accept': 'application/json'},
              json={'version': '0.1.2', 'gitcommithash': 'hashyhash', 'servertime': 3})
        kbuh = build_lookup({'url': 'http://whee.com', 'token': 'foo', 'admin-role': 'admin'})
        assert kbuh.auth_url == 'http://whee.com/'
        # reach into the implementation here to avoid running all tests twice, one for constructor,
        # one for builder. Outweights the bad practice here
        assert kbuh._token == Token('foo')
        assert kbuh._kbase_system_admin == 'admin'


def test_init_with_builder_fail_missing_input():
    ok = {'token': 't', 'admin-role': 'foo', 'url': 'http://foobar.com'}
    notok = copy.copy(ok)
    del notok['url']
    fail_init_with_builder(notok, LookupInitializationError(
        'kbase user lookup handler requires url configuration item'))

    notok = copy.copy(ok)
    del notok['token']
    fail_init_with_builder(notok, LookupInitializationError(
        'kbase user lookup handler requires token configuration item'))

    notok = copy.copy(ok)
    del notok['admin-role']
    fail_init_with_builder(notok, LookupInitializationError(
        'kbase user lookup handler requires admin-role configuration item'))


def fail_init_with_builder(cfg, expected):
    with raises(Exception) as got:
        build_lookup(cfg)
    assert_exception_correct(got.value, expected)


def test_init_fail_None_input():
    fail_init(None, Token('foo'), 'admin', TypeError('kbase_auth_url cannot be None'))
    fail_init('url', None, 'admin', TypeError('kbase_token cannot be None'))
    fail_init('url', Token('foo'), None, TypeError('kbase_system_admin cannot be None'))


def test_init_fail_not_json(log_collector):
    html = '<html><body>Sorry mylittleponypron.com has been shut down</body></html>'
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/',
              request_headers={'Accept': 'application/json'},
              status_code=404,
              text=html)

        fail_init('http://my1stauthservice.com/', Token('foo'), 'admin',
                  IOError('Non-JSON response from KBase auth server, status code: 404'))

    assert_logs_correct(
        log_collector, 'Non-JSON response from KBase auth server, status code: 404, response:\n' +
        html)


def test_init_fail_auth_returned_error():
    # there isn't really a believable error the auth service could generate at the root, so
    # we just use any old error
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/',
              request_headers={'Accept': 'application/json'},
              status_code=401,
              json={'error': {'apperror': 'Authentication failed',
                              'message': '10000 Authentication failed: crap'}})

        fail_init('http://my1stauthservice.com', Token('foo'), 'admin',
                  IOError('Error from KBase auth server: 10000 Authentication failed: crap'))


def test_init_fail_missing_keys():
    check_missing_keys({}, "['gitcommithash', 'servertime', 'version']")
    check_missing_keys({'version': '0.1'}, "['gitcommithash', 'servertime']")
    check_missing_keys({'servertime': 42, 'gitcommithash': 'somehash'}, "['version']")


def check_missing_keys(json, missing_keys):
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/',
              request_headers={'Accept': 'application/json'},
              json=json)

        fail_init('http://my1stauthservice.com', Token('foo'), 'admin', IOError(
            'http://my1stauthservice.com/ does not appear to be the KBase auth server. ' +
            'The root JSON response does not contain the expected keys ' + missing_keys))


def fail_init(url, token, kbase_admin_str, expected):
    with raises(Exception) as got:
        KBaseUserLookup(url, token, kbase_admin_str)
    assert_exception_correct(got.value, expected)


def get_user_handler(url, token, kbase_admin_role):
    newurl = url
    if not url.endswith('/'):
        newurl = url + '/'

    with requests_mock.Mocker() as m:
        m.get(newurl,
              request_headers={'Accept': 'application/json'},
              json={'version': '0.1.2', 'gitcommithash': 'hashyhash', 'servertime': 3})
        return KBaseUserLookup(url, token, kbase_admin_role)


def test_get_authsource_id():
    kbuh = get_user_handler('http://url.com', Token('foo'), 'admin')
    assert kbuh.get_authsource_id() == AuthsourceID('kbase')


def test_get_user():
    check_get_user(False, ['foo', 'bar'])
    check_get_user(True, ['foo', 'bar', 'mapping_admin'])


def check_get_user(isadmin, customroles):
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/token',
              request_headers={'Authorization': 'bar'},
              json={'user': 'u1', 'expires': 4800, 'cachefor': 5600})

        m.get('http://my1stauthservice.com/api/api/V2/me',
              request_headers={'Authorization': 'bar'},
              json={'customroles': customroles})

        kbuh = get_user_handler('http://my1stauthservice.com/api', Token('foo'), 'mapping_admin')

        assert kbuh.get_user(Token('bar')) == \
            (User(AuthsourceID('kbase'), Username('u1')), isadmin, 4, 5)


def test_get_user_fail_None_input():
    kbuh = get_user_handler('http://my1stauthservice.com/api', Token('foo'), 'admin')
    fail_get_user(kbuh, None, TypeError('token cannot be None'))


def test_get_user_fail_not_json_token(log_collector):
    html = '<html><body>Sorry gopsasquatchpron.com has been shut down</body></html>'
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/token',
              request_headers={'Authorization': 'bar'},
              status_code=404,
              text=html)

        kbuh = get_user_handler('http://my1stauthservice.com/api', Token('foo'), 'admin')

        fail_get_user(kbuh, Token('bar'),
                      IOError('Non-JSON response from KBase auth server, status code: 404'))

    assert_logs_correct(
        log_collector, 'Non-JSON response from KBase auth server, status code: 404, response:\n' +
        html)


def test_get_user_fail_invalid_token_token():
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/token',
              request_headers={'Authorization': 'bar'},
              status_code=401,
              json={'error': {'apperror': 'Invalid token', 'message': '10020 Invalid token'}})

        kbuh = get_user_handler('http://my1stauthservice.com/api', Token('foo'), 'admin')

        fail_get_user(kbuh, Token('bar'), InvalidTokenError(
            'KBase auth server reported token is invalid.'))


def test_get_user_fail_auth_returned_other_error_token():
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/token',
              request_headers={'Authorization': 'bar'},
              status_code=401,
              json={'error': {'apperror': 'Authentication failed',
                              'message': '10000 Authentication failed: crap'}})

        kbuh = get_user_handler('http://my1stauthservice.com/api', Token('foo'), 'admin')

        fail_get_user(kbuh, Token('bar'),
                      IOError('Error from KBase auth server: 10000 Authentication failed: crap'))


def test_get_user_fail_not_json_me(log_collector):
    html = '<html><body>Sorry notthensa.com has been shut down</body></html>'
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/token',
              request_headers={'Authorization': 'bar'},
              json={'user': 'u1', 'expires': 2000, 'cachefor': 3000})

        m.get('http://my1stauthservice.com/api/api/V2/me',
              request_headers={'Authorization': 'bar'},
              status_code=404,
              text=html)

        kbuh = get_user_handler('http://my1stauthservice.com/api', Token('foo'), 'mapping_admin')

        fail_get_user(kbuh, Token('bar'),
                      IOError('Non-JSON response from KBase auth server, status code: 404'))

    assert_logs_correct(
        log_collector, 'Non-JSON response from KBase auth server, status code: 404, response:\n' +
        html)


def test_get_user_fail_invalid_token_me():
    # this should basically be impossible, but it doesn't hurt to test it
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/token',
              request_headers={'Authorization': 'bar'},
              json={'user': 'u1', 'expires': 2000, 'cachefor': 3000})

        m.get('http://my1stauthservice.com/api/api/V2/me',
              request_headers={'Authorization': 'bar'},
              status_code=401,
              json={'error': {'apperror': 'Invalid token', 'message': '10020 Invalid token'}})

        kbuh = get_user_handler('http://my1stauthservice.com/api', Token('foo'), 'admin')

        fail_get_user(kbuh, Token('bar'), InvalidTokenError(
            'KBase auth server reported token is invalid.'))


def test_get_user_fail_auth_returned_other_error_me():
    # this should basically be impossible, but it doesn't hurt to test it
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/token',
              request_headers={'Authorization': 'bar'},
              json={'user': 'u1', 'expires': 2000, 'cachefor': 3000})

        m.get('http://my1stauthservice.com/api/api/V2/me',
              request_headers={'Authorization': 'bar'},
              status_code=401,
              json={'error': {'apperror': 'Authentication failed',
                              'message': '10000 Authentication failed: crap'}})

        kbuh = get_user_handler('http://my1stauthservice.com/api', Token('foo'), 'admin')

        fail_get_user(kbuh, Token('bar'),
                      IOError('Error from KBase auth server: 10000 Authentication failed: crap'))


def fail_get_user(kbuh, token, expected):
    with raises(Exception) as got:
        kbuh.get_user(token)
    assert_exception_correct(got.value, expected)


def test_is_valid_user():
    check_is_valid_user({'imauser': 'I am, indeed, a user'}, True)
    check_is_valid_user({}, False)


def check_is_valid_user(json, result):
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/users/?list=imauser',
              request_headers={'Authorization': 'foo'},
              json=json)

        kbuh = get_user_handler('http://my1stauthservice.com/api/', Token('foo'), 'admin')

        assert kbuh.is_valid_user(Username('imauser')) == (result, None, 3600)


def test_is_valid_user_fail_None_input():
    kbuh = get_user_handler('http://my1stauthservice.com/api', Token('foo'), 'admin')
    fail_is_valid_user(kbuh, None, TypeError('username cannot be None'))


def test_is_valid_user_fail_not_json(log_collector):
    html = '<html><body>Sorry oscarthegrouchpron.com has been shut down</body></html>'
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/users/?list=supahusah',
              request_headers={'Authorization': 'foo'},
              status_code=502,
              text=html)

        kbuh = get_user_handler('http://my1stauthservice.com/api', Token('foo'), 'admin')

        fail_is_valid_user(kbuh, Username('supahusah'),
                           IOError('Non-JSON response from KBase auth server, status code: 502'))

    assert_logs_correct(
        log_collector, 'Non-JSON response from KBase auth server, status code: 502, response:\n' +
        html)


def test_is_valid_user_fail_invalid_token():
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/users/?list=supausah3',
              request_headers={'Authorization': 'foo'},
              status_code=401,
              json={'error': {'apperror': 'Invalid token', 'message': '10020 Invalid token'}})

        kbuh = get_user_handler('http://my1stauthservice.com/api', Token('foo'), 'admin')

        fail_is_valid_user(kbuh, Username('supausah3'), InvalidTokenError(
            'KBase auth server reported token is invalid.'))


def test_is_valid_user_fail_auth_returned_other_error():
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/users/?list=supausah2',
              request_headers={'Authorization': 'baz'},
              status_code=400,
              json={'error': {'apperror': 'Authentication failed',
                              'message': '10000 Authentication failed: crap'}})

        kbuh = get_user_handler('http://my1stauthservice.com/api', Token('baz'), 'admin')

        fail_is_valid_user(kbuh, Username('supausah2'), IOError(
            'Error from KBase auth server: 10000 Authentication failed: crap'))


def fail_is_valid_user(kbuh, username, expected):
    with raises(Exception) as got:
        kbuh.is_valid_user(username)
    assert_exception_correct(got.value, expected)
