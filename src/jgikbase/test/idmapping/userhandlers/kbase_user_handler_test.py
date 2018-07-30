from jgikbase.idmapping.userhandlers.kbase_user_handler import KBaseUserHandler
from jgikbase.idmapping.core.user import AuthsourceID, User, Username
from jgikbase.idmapping.core.tokens import Token
import requests_mock
from pytest import raises
from jgikbase.test.idmapping.test_utils import assert_exception_correct
from jgikbase.idmapping.core.errors import InvalidTokenError


def test_init():
    kbuh = KBaseUserHandler('url', Token('foo'), 'admin')
    assert kbuh.auth_url == 'url/'


def test_init_fail_None_input():
    fail_init(None, Token('foo'), 'admin', TypeError('kbase_auth_url cannot be None'))
    fail_init('url', None, 'admin', TypeError('kbase_token cannot be None'))
    fail_init('url', Token('foo'), None, TypeError('kbase_system_admin cannot be None'))


def fail_init(url, token, kbase_admin_str, expected):
    with raises(Exception) as got:
        KBaseUserHandler(url, token, kbase_admin_str)
    assert_exception_correct(got.value, expected)


def test_get_authsource_id():
    kbuh = KBaseUserHandler('url', Token('foo'), 'admin')
    assert kbuh.get_authsource_id() == AuthsourceID('kbase')


def test_get_user():
    check_get_user(False, ['foo', 'bar'])
    check_get_user(True, ['foo', 'bar', 'mapping_admin'])


def check_get_user(isadmin, customroles):
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/token',
              request_headers={'Authorization': 'bar'},
              json={'user': 'u1'})

        m.get('http://my1stauthservice.com/api/api/V2/me',
              request_headers={'Authorization': 'bar'},
              json={'customroles': customroles})

        kbuh = KBaseUserHandler('http://my1stauthservice.com/api', Token('foo'), 'mapping_admin')

        assert kbuh.get_user(Token('bar')) == \
            (User(AuthsourceID('kbase'), Username('u1')), isadmin)


def test_get_user_fail_None_input():
    kbuh = KBaseUserHandler('http://my1stauthservice.com/api', Token('foo'), 'admin')
    fail_get_user(kbuh, None, TypeError('token cannot be None'))


def test_get_user_fail_not_json_token():
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/token',
              request_headers={'Authorization': 'bar'},
              status_code=404,
              text='<html><body>Sorry turtlepron.com has been shut down</body></html>')

        kbuh = KBaseUserHandler('http://my1stauthservice.com/api', Token('foo'), 'admin')

        fail_get_user(kbuh, Token('bar'),
                      IOError('Non-JSON response from KBase auth server, status code: 404'))


def test_get_user_fail_invalid_token_token():
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/token',
              request_headers={'Authorization': 'bar'},
              status_code=401,
              json={'error': {'appcode': 10020, 'message': '10020 Invalid token'}})

        kbuh = KBaseUserHandler('http://my1stauthservice.com/api', Token('foo'), 'admin')

        fail_get_user(kbuh, Token('bar'), InvalidTokenError(
            'KBase auth server reported token is invalid.'))


def test_get_user_fail_auth_returned_other_error_token():
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/token',
              request_headers={'Authorization': 'bar'},
              status_code=401,
              json={'error': {'appcode': 10000, 'message': '10000 Authentication failed: crap'}})

        kbuh = KBaseUserHandler('http://my1stauthservice.com/api', Token('foo'), 'admin')

        fail_get_user(kbuh, Token('bar'),
                      IOError('Error from KBase auth server: 10000 Authentication failed: crap'))


def test_get_user_fail_not_json_me():
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/token',
              request_headers={'Authorization': 'bar'},
              json={'user': 'u1'})

        m.get('http://my1stauthservice.com/api/api/V2/me',
              request_headers={'Authorization': 'bar'},
              status_code=404,
              text='<html><body>Sorry notthensa.com has been shut down</body></html>')

        kbuh = KBaseUserHandler('http://my1stauthservice.com/api', Token('foo'), 'mapping_admin')

        fail_get_user(kbuh, Token('bar'),
                      IOError('Non-JSON response from KBase auth server, status code: 404'))


def test_get_user_fail_invalid_token_me():
    # this should basically be impossible, but it doesn't hurt to test it
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/token',
              request_headers={'Authorization': 'bar'},
              json={'user': 'u1'})

        m.get('http://my1stauthservice.com/api/api/V2/me',
              request_headers={'Authorization': 'bar'},
              status_code=401,
              json={'error': {'appcode': 10020, 'message': '10020 Invalid token'}})

        kbuh = KBaseUserHandler('http://my1stauthservice.com/api', Token('foo'), 'admin')

        fail_get_user(kbuh, Token('bar'), InvalidTokenError(
            'KBase auth server reported token is invalid.'))


def test_get_user_fail_auth_returned_other_error_me():
    # this should basically be impossible, but it doesn't hurt to test it
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/token',
              request_headers={'Authorization': 'bar'},
              json={'user': 'u1'})

        m.get('http://my1stauthservice.com/api/api/V2/me',
              request_headers={'Authorization': 'bar'},
              status_code=401,
              json={'error': {'appcode': 10000, 'message': '10000 Authentication failed: crap'}})

        kbuh = KBaseUserHandler('http://my1stauthservice.com/api', Token('foo'), 'admin')

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

        kbuh = KBaseUserHandler('http://my1stauthservice.com/api/', Token('foo'), 'admin')

        assert kbuh.is_valid_user(Username('imauser')) is result


def test_is_valid_user_fail_None_input():
    kbuh = KBaseUserHandler('http://my1stauthservice.com/api', Token('foo'), 'admin')
    fail_is_valid_user(kbuh, None, TypeError('username cannot be None'))


def test_is_valid_user_fail_not_json():
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/users/?list=supahusah',
              request_headers={'Authorization': 'foo'},
              status_code=502,
              text='<html><body>Sorry oscarthegrouchpron.com has been shut down</body></html>')

        kbuh = KBaseUserHandler('http://my1stauthservice.com/api', Token('foo'), 'admin')

        fail_is_valid_user(kbuh, Username('supahusah'),
                           IOError('Non-JSON response from KBase auth server, status code: 502'))


def test_is_valid_user_fail_invalid_token():
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/users/?list=supausah3',
              request_headers={'Authorization': 'foo'},
              status_code=401,
              json={'error': {'appcode': 10020, 'message': '10020 Invalid token'}})

        kbuh = KBaseUserHandler('http://my1stauthservice.com/api', Token('foo'), 'admin')

        fail_is_valid_user(kbuh, Username('supausah3'), InvalidTokenError(
            'KBase auth server reported token is invalid.'))


def test_is_valid_user_fail_auth_returned_other_error():
    with requests_mock.Mocker() as m:
        m.get('http://my1stauthservice.com/api/api/V2/users/?list=supausah2',
              request_headers={'Authorization': 'baz'},
              status_code=400,
              json={'error': {'appcode': 10000, 'message': '10000 Authentication failed: crap'}})

        kbuh = KBaseUserHandler('http://my1stauthservice.com/api', Token('baz'), 'admin')

        fail_is_valid_user(kbuh, Username('supausah2'), IOError(
            'Error from KBase auth server: 10000 Authentication failed: crap'))


def fail_is_valid_user(kbuh, username, expected):
    with raises(Exception) as got:
        kbuh.is_valid_user(username)
    assert_exception_correct(got.value, expected)
