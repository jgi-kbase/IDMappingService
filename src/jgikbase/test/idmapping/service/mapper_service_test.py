from unittest.mock import create_autospec
from jgikbase.idmapping.core.mapper import IDMapper
from jgikbase.idmapping.service.mapper_service import create_app
from jgikbase.idmapping.builder import IDMappingBuilder
from jgikbase.idmapping.core.object_id import Namespace, NamespaceID
from jgikbase.idmapping.core.user import AuthsourceID, User, Username
from jgikbase.idmapping.core.tokens import Token
from jgikbase.idmapping.core.errors import InvalidTokenError, NoSuchNamespaceError


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

    assert mapper.get_namespace.call_args_list == [((NamespaceID('foo'),), {})]


def test_get_namespace_with_auth():
    cli, mapper = build_app()
    mapper.get_namespace.return_value = Namespace(NamespaceID('foo'), True, set([
        User(AuthsourceID('bar'), Username('baz')), User(AuthsourceID('bag'), Username('bat'))]))

    resp = cli.get('/api/v1/namespace/foo', headers={'Authorization': 'as toketoketoke'})

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
