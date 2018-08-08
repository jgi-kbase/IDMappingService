from unittest.mock import create_autospec
from jgikbase.idmapping.core.mapper import IDMapper
from jgikbase.idmapping.service.mapper_service import create_app
from jgikbase.idmapping.builder import IDMappingBuilder
from jgikbase.idmapping.core.object_id import Namespace, NamespaceID
from jgikbase.idmapping.core.user import AuthsourceID, User, Username
from jgikbase.idmapping.core.tokens import Token
from jgikbase.idmapping.core.errors import InvalidTokenError, NoSuchNamespaceError,\
    UnauthorizedError


def build_app():
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    mapper = create_autospec(IDMapper, spec_set=True, instance=True)
    builder.build_id_mapping_system.return_value = mapper

    app = create_app(builder)
    cli = app.test_client()

    return cli, mapper


def test_get_namespace_no_auth():
    cli, mapper = build_app()
    mapper.get_namespace.return_value = Namespace(NamespaceID('foo'), False)

    resp = cli.get('/api/v1/namespace/foo')

    assert resp.get_json() == {'namespace': 'foo', 'publicly_mappable': False, 'users': []}
    assert resp.status_code == 200

    assert mapper.get_namespace.call_args_list == [((NamespaceID('foo'), None, None), {})]


def test_get_namespace_with_auth():
    cli, mapper = build_app()
    mapper.get_namespace.return_value = Namespace(NamespaceID('foo'), True, set([
        User(AuthsourceID('bar'), Username('baz')), User(AuthsourceID('bag'), Username('bat'))]))

    resp = cli.get('/api/v1/namespace/foo', headers={'Authorization': '  \tas toketoketoke  \t'})

    assert resp.get_json() == {'namespace': 'foo', 'publicly_mappable': True,
                               'users': ['bag/bat', 'bar/baz']}
    assert resp.status_code == 200

    assert mapper.get_namespace.call_args_list == [((NamespaceID('foo'), AuthsourceID('as'),
                                                     Token('toketoketoke')), {})]


def test_get_namespace_fail_munged_auth():
    cli, _ = build_app()
    resp = cli.get('/api/v1/namespace/foo', headers={'Authorization': 'astoketoketoke'})

    assert resp.get_json() == {
        'error': {'httpcode': 400,
                  'httpstatus': 'Bad Request',
                  'appcode': 30001,
                  'apperror': 'Illegal input parameter',
                  'message': ('30001 Illegal input parameter: ' +
                              'Expected authsource and token in header.')
                  }
        }
    assert resp.status_code == 400


def test_get_namespace_fail_invalid_token():
    # really a general test of the authentication error handler
    cli, mapper = build_app()
    mapper.get_namespace.side_effect = InvalidTokenError()

    resp = cli.get('/api/v1/namespace/foo', headers={'Authorization': 'as toketoketoke'})

    assert resp.get_json() == {
        'error': {'httpcode': 401,
                  'httpstatus': 'Unauthorized',
                  'appcode': 10020,
                  'apperror': 'Invalid token',
                  'message': '10020 Invalid token'
                  }
        }
    assert resp.status_code == 401


def test_get_namespace_fail_no_namespace():
    # really a general test of the no data error handler
    cli, mapper = build_app()
    mapper.get_namespace.side_effect = NoSuchNamespaceError('foo')

    resp = cli.get('/api/v1/namespace/foo')

    assert resp.get_json() == {
        'error': {'httpcode': 404,
                  'httpstatus': 'Not Found',
                  'appcode': 50010,
                  'apperror': 'No such namespace',
                  'message': '50010 No such namespace: foo'
                  }
        }
    assert resp.status_code == 404


def test_get_namespace_fail_valueerror():
    # really a general test of the catch all error handler
    cli, mapper = build_app()
    mapper.get_namespace.side_effect = ValueError('things are all messed up down here')

    resp = cli.get('/api/v1/namespace/foo')

    assert resp.get_json() == {
        'error': {'httpcode': 500,
                  'httpstatus': 'Internal Server Error',
                  'message': 'things are all messed up down here'
                  }
        }
    assert resp.status_code == 500


def test_method_not_allowed():
    cli, _ = build_app()

    resp = cli.delete('/api/v1/namespace/foo')

    assert resp.get_json() == {
        'error': {'httpcode': 405,
                  'httpstatus': 'Method Not Allowed',
                  'message': ('405 Method Not Allowed: The method is not allowed ' +
                              'for the requested URL.')
                  }
        }
    assert resp.status_code == 405


def test_not_found():
    cli, _ = build_app()

    resp = cli.get('/api/v1/nothinghere')

    assert resp.get_json() == {
        'error': {'httpcode': 404,
                  'httpstatus': 'Not Found',
                  'message': ('404 Not Found: The requested URL was not found on the server.  ' +
                              'If you entered the URL manually please check your spelling ' +
                              'and try again.')
                  }
        }
    assert resp.status_code == 404


def test_create_namespace_put():
    cli, mapper = build_app()

    resp = cli.put('/api/v1/namespace/foo', headers={'Authorization': 'source tokey'})

    assert resp.data == b''
    assert resp.status_code == 204

    assert mapper.create_namespace.call_args_list == [((
        AuthsourceID('source'), Token('tokey'), NamespaceID('foo')), {})]


def test_create_namespace_post():
    cli, mapper = build_app()

    resp = cli.post('/api/v1/namespace/foo', headers={'Authorization': 'source tokey'})

    assert resp.data == b''
    assert resp.status_code == 204

    assert mapper.create_namespace.call_args_list == [((
        AuthsourceID('source'), Token('tokey'), NamespaceID('foo')), {})]


def test_create_namespace_fail_no_token():
    fail_no_token_put('/api/v1/namespace/foo')


def fail_no_token_put(url):
    cli, _ = build_app()
    resp = cli.put(url)
    fail_no_token_check(resp)


def fail_no_token_delete(url):
    cli, _ = build_app()
    resp = cli.delete(url)
    fail_no_token_check(resp)


def fail_no_token_check(resp):
    assert resp.get_json() == {
        'error': {'httpcode': 401,
                  'appcode': 10010,
                  'apperror': 'No authentication token',
                  'httpstatus': 'Unauthorized',
                  'message': '10010 No authentication token'
                  }
        }
    assert resp.status_code == 401


def test_create_namespace_fail_munged_auth():
    fail_munged_auth_post('/api/v1/namespace/foo')
    fail_munged_auth_put('/api/v1/namespace/foo')


def fail_munged_auth_put(url):
    cli, _ = build_app()
    resp = cli.put(url, headers={'Authorization': 'astoketoketoke'})
    fail_munged_auth_check(resp)


def fail_munged_auth_post(url):
    cli, _ = build_app()
    resp = cli.post(url, headers={'Authorization': 'astoketoketoke'})
    fail_munged_auth_check(resp)


def fail_munged_auth_delete(url):
    cli, _ = build_app()
    resp = cli.delete(url, headers={'Authorization': 'astoketoketoke'})
    fail_munged_auth_check(resp)


def fail_munged_auth_check(resp):
    assert resp.get_json() == {
        'error': {'httpcode': 400,
                  'httpstatus': 'Bad Request',
                  'appcode': 30001,
                  'apperror': 'Illegal input parameter',
                  'message': ('30001 Illegal input parameter: ' +
                              'Expected authsource and token in header.')
                  }
        }
    assert resp.status_code == 400


def test_create_namespace_fail_illegal_ns_id():
    fail_illegal_ns_id_put('/api/v1/namespace/foo&bar')


def fail_illegal_ns_id_put(url):
    cli, _ = build_app()
    resp = cli.put(url, headers={'Authorization': 'source tokey'})
    fail_illegal_ns_id_check(resp)


def fail_illegal_ns_id_delete(url):
    cli, _ = build_app()
    resp = cli.delete(url, headers={'Authorization': 'source tokey'})
    fail_illegal_ns_id_check(resp)


def fail_illegal_ns_id_check(resp):
    assert resp.get_json() == {
        'error': {'httpcode': 400,
                  'httpstatus': 'Bad Request',
                  'appcode': 30001,
                  'apperror': 'Illegal input parameter',
                  'message': ('30001 Illegal input parameter: ' +
                              'Illegal character in namespace id foo&bar: &')
                  }
        }
    assert resp.status_code == 400


def test_create_namespace_fail_unauthorized():
    # general test of the unauthorized error handler
    cli, mapper = build_app()

    mapper.create_namespace.side_effect = UnauthorizedError('YOU SHALL NOT PASS')

    resp = cli.put('/api/v1/namespace/foo', headers={'Authorization': 'source tokey'})

    assert resp.get_json() == {
        'error': {'httpcode': 403,
                  'httpstatus': 'Forbidden',
                  'appcode': 20000,
                  'apperror': 'Unauthorized',
                  'message': '20000 Unauthorized: YOU SHALL NOT PASS'
                  }
        }
    assert resp.status_code == 403

    assert mapper.create_namespace.call_args_list == [((
        AuthsourceID('source'), Token('tokey'), NamespaceID('foo')), {})]


def test_add_user_to_namespace():
    cli, mapper = build_app()

    resp = cli.put('/api/v1/namespace/foo/user/bar/baz', headers={'Authorization': 'source tokey'})

    assert resp.data == b''
    assert resp.status_code == 204

    assert mapper.add_user_to_namespace.call_args_list == [((
        AuthsourceID('source'), Token('tokey'), NamespaceID('foo'),
        User(AuthsourceID('bar'), Username('baz'))), {})]


def test_add_user_to_namespace_fail_no_token():
    fail_no_token_put('/api/v1/namespace/foo/user/bar/baz')


def test_add_user_to_namespace_fail_munged_auth():
    fail_munged_auth_put('/api/v1/namespace/foo/user/bar/baz')


def test_add_user_to_namespace_fail_illegal_ns_id():
    fail_illegal_ns_id_put('/api/v1/namespace/foo&bar/user/bar/baz')


def test_remove_user_from_namespace():
    cli, mapper = build_app()

    resp = cli.delete('/api/v1/namespace/foo/user/bar/baz',
                      headers={'Authorization': 'source tokey'})

    assert resp.data == b''
    assert resp.status_code == 204

    assert mapper.remove_user_from_namespace.call_args_list == [((
        AuthsourceID('source'), Token('tokey'), NamespaceID('foo'),
        User(AuthsourceID('bar'), Username('baz'))), {})]


def test_remove_user_from_namespace_fail_no_token():
    fail_no_token_delete('/api/v1/namespace/foo/user/bar/baz')


def test_remove_user_from_namespace_fail_munged_auth():
    fail_munged_auth_delete('/api/v1/namespace/foo/user/bar/baz')


def test_remove_user_from_namespace_fail_illegal_ns_id():
    fail_illegal_ns_id_delete('/api/v1/namespace/foo&bar/user/bar/baz')


def test_set_namespace_publicly_mappable():
    check_set_namespace_publicly_mappable('true', True)
    check_set_namespace_publicly_mappable('false', False)


def check_set_namespace_publicly_mappable(arg, expected):
    cli, mapper = build_app()

    resp = cli.put('/api/v1/namespace/foo/set?publicly_mappable=' + arg,
                   headers={'Authorization': 'source tokey'})

    assert resp.data == b''
    assert resp.status_code == 204

    assert mapper.set_namespace_publicly_mappable.call_args_list == [((
        AuthsourceID('source'), Token('tokey'), NamespaceID('foo'), expected), {})]


def test_set_namespace_no_op():
    cli, mapper = build_app()

    resp = cli.put('/api/v1/namespace/foo/set', headers={'Authorization': 'source tokey'})

    assert resp.data == b''
    assert resp.status_code == 204

    assert mapper.set_namespace_publicly_mappable.call_args_list == []


def test_set_namespace_publicly_mappable_illegal_input():
    cli, _ = build_app()

    resp = cli.put('/api/v1/namespace/foo/set?publicly_mappable=foobar',
                   headers={'Authorization': 'source tokey'})

    assert resp.get_json() == {
        'error': {'httpcode': 400,
                  'httpstatus': 'Bad Request',
                  'appcode': 30001,
                  'apperror': 'Illegal input parameter',
                  'message': ("30001 Illegal input parameter: Expected value of 'true' or " +
                              "'false' for publicly_mappable")
                  }
        }
    assert resp.status_code == 400


def test_set_namespace_publicly_mappable_fail_no_token():
    fail_no_token_put('/api/v1/namespace/foo/set')


def test_set_namespace_publicly_mappable_fail_munged_auth():
    fail_munged_auth_put('/api/v1/namespace/foo/set')


def test_set_namespace_publicly_mappable_fail_illegal_ns_id():
    fail_illegal_ns_id_put('/api/v1/namespace/foo&bar/set?publicly_mappable=true')
