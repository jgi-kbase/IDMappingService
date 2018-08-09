from unittest.mock import create_autospec
from jgikbase.idmapping.core.mapper import IDMapper
from jgikbase.idmapping.service.mapper_service import create_app
from jgikbase.idmapping.builder import IDMappingBuilder
from jgikbase.idmapping.core.object_id import Namespace, NamespaceID, ObjectID
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
    fail_illegal_ns_id_put('/api/v1/namespace/foo*bar')


def fail_illegal_ns_id_get(url, json=None):
    cli, _ = build_app()
    resp = cli.get(url, headers={'Authorization': 'source tokey'}, json=json)
    fail_illegal_ns_id_check(resp)


def fail_illegal_ns_id_put(url, json=None):
    cli, _ = build_app()
    resp = cli.put(url, headers={'Authorization': 'source tokey'}, json=json)
    fail_illegal_ns_id_check(resp)


def fail_illegal_ns_id_delete(url, json=None):
    cli, _ = build_app()
    resp = cli.delete(url, headers={'Authorization': 'source tokey'}, json=json)
    fail_illegal_ns_id_check(resp)


def fail_illegal_ns_id_check(resp):
    assert resp.get_json() == {
        'error': {'httpcode': 400,
                  'httpstatus': 'Bad Request',
                  'appcode': 30001,
                  'apperror': 'Illegal input parameter',
                  'message': ('30001 Illegal input parameter: ' +
                              'Illegal character in namespace id foo*bar: *')
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
    fail_illegal_ns_id_put('/api/v1/namespace/foo*bar/user/bar/baz')


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
    fail_illegal_ns_id_delete('/api/v1/namespace/foo*bar/user/bar/baz')


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
    fail_illegal_ns_id_put('/api/v1/namespace/foo*bar/set?publicly_mappable=true')


def test_get_namespaces_empty():
    check_get_namespaces((set(), set()), {'publicly_mappable': [], 'privately_mappable': []})


def test_get_namespaces_public():
    check_get_namespaces(
        (set([NamespaceID('zedsdead'), NamespaceID('foo'), NamespaceID('bar')]), set()),
        {'publicly_mappable': ['bar', 'foo', 'zedsdead'], 'privately_mappable': []})


def test_get_namespaces_private():
    check_get_namespaces(
        (set(), set([NamespaceID('zedsdead'), NamespaceID('foo'), NamespaceID('bar')])),
        {'publicly_mappable': [], 'privately_mappable': ['bar', 'foo', 'zedsdead']})


def test_get_namespaces_both():
    check_get_namespaces(
        (set([NamespaceID('whoo'), NamespaceID('whee'), NamespaceID('pewpewpew')]),
         set([NamespaceID('zedsdead'), NamespaceID('foo'), NamespaceID('bar')])),
        {'publicly_mappable': ['pewpewpew', 'whee', 'whoo'],
         'privately_mappable': ['bar', 'foo', 'zedsdead']})


def check_get_namespaces(returned, expected):
    cli, mapper = build_app()

    mapper.get_namespaces.return_value = returned

    resp = cli.get('/api/v1/namespace/')

    assert resp.get_json() == expected
    assert resp.status_code == 200

    assert mapper.get_namespaces.call_args_list == [((), {})]


def test_create_mapping_put():
    cli, mapper = build_app()
    resp = cli.put('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                   json={'admin_id': 'aid', 'other_id': 'id'})
    check_create_mapping(resp, mapper)


def test_create_mapping_post():
    cli, mapper = build_app()
    resp = cli.post('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                    json={'admin_id': 'aid', 'other_id': 'id'})
    check_create_mapping(resp, mapper)


def check_create_mapping(resp, mapper):
    assert resp.data == b''
    assert resp.status_code == 204

    assert mapper.create_mapping.call_args_list == [((
        AuthsourceID('source'), Token('tokey'),
        ObjectID(NamespaceID('ans'), 'aid'),
        ObjectID(NamespaceID('ns'), 'id')), {})]


def test_create_mapping_fail_no_token():
    fail_no_token_put('/api/v1/mapping/ans/ns')


def test_create_mapping_fail_munged_auth():
    fail_munged_auth_put('/api/v1/mapping/ans/ns')
    fail_munged_auth_post('/api/v1/mapping/ans/ns')


def test_create_mapping_fail_no_body():
    cli, _ = build_app()
    resp = cli.put('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'})
    check_mapping_fail_no_body(resp)


def check_mapping_fail_no_body(resp):
    assert resp.get_json() == {
        'error': {'httpcode': 400,
                  'httpstatus': 'Bad Request',
                  'message': 'Input JSON decode error: Expecting value: line 1 column 1 (char 0)'
                  }
        }
    assert resp.status_code == 400


def test_create_mapping_fail_bad_json():
    cli, _ = build_app()
    resp = cli.put('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                   data='{"foo": ["bar", "baz"}]')
    check_mapping_fail_bad_json(resp)


def check_mapping_fail_bad_json(resp):
    assert resp.get_json() == {
        'error': {'httpcode': 400,
                  'httpstatus': 'Bad Request',
                  'message': ("Input JSON decode error: Expecting ',' delimiter: " +
                              "line 1 column 22 (char 21)")
                  }
        }
    assert resp.status_code == 400


def test_create_mapping_fail_not_dict():
    cli, _ = build_app()
    resp = cli.put('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                   json=['foo', 'bar'])
    check_mapping_fail_not_dict(resp)


def check_mapping_fail_not_dict(resp):
    assert resp.get_json() == {
        'error': {'httpcode': 400,
                  'httpstatus': 'Bad Request',
                  'appcode': 30001,
                  'apperror': 'Illegal input parameter',
                  'message': ('30001 Illegal input parameter: ' +
                              'Expected JSON mapping in request body')
                  }
        }
    assert resp.status_code == 400


def test_create_mapping_fail_missing_id():
    check_create_mapping_fail_missing_id(None)
    check_create_mapping_fail_missing_id([])


def check_create_mapping_fail_missing_id(id_):
    cli, _ = build_app()
    resp = cli.put('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                   json={'admin_id': id_})
    check_mapping_fail_missing_id(resp, 'admin_id')

    resp = cli.put('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                   json={'other_id': id_, 'admin_id': 'id'})
    check_mapping_fail_missing_id(resp, 'other_id')


def check_mapping_fail_missing_id(resp, idname):
    assert resp.get_json() == {
        'error': {'httpcode': 400,
                  'httpstatus': 'Bad Request',
                  'appcode': 30001,
                  'apperror': 'Illegal input parameter',
                  'message': ('30001 Illegal input parameter: ' +
                              'Expected string for parameter ' + idname)
                  }
        }
    assert resp.status_code == 400


def test_create_mapping_fail_whitespace_id():
    cli, _ = build_app()
    resp = cli.put('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                   json={'admin_id': '    \t    '})
    check_mapping_fail_whitespace_id(resp, 'admin_id')

    resp = cli.put('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                   json={'other_id': '    \t    ', 'admin_id': 'id'})
    check_mapping_fail_whitespace_id(resp, 'other_id')


def check_mapping_fail_whitespace_id(resp, idname):
    assert resp.get_json() == {
        'error': {'httpcode': 400,
                  'httpstatus': 'Bad Request',
                  'appcode': 30000,
                  'apperror': 'Missing input parameter',
                  'message': '30000 Missing input parameter: ' + idname
                  }
        }
    assert resp.status_code == 400


def test_create_mapping_fail_illegal_ns_id():
    fail_illegal_ns_id_put('/api/v1/mapping/foo*bar/ns',
                           json={'admin_id': 'aid', 'other_id': 'id'})


def test_remove_mapping():
    cli, mapper = build_app()

    resp = cli.delete('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                      json={'admin_id': 'aid', 'other_id': 'id'})

    assert resp.data == b''
    assert resp.status_code == 204

    assert mapper.remove_mapping.call_args_list == [((
        AuthsourceID('source'), Token('tokey'),
        ObjectID(NamespaceID('ans'), 'aid'),
        ObjectID(NamespaceID('ns'), 'id')), {})]


def test_remove_mapping_fail_no_token():
    fail_no_token_delete('/api/v1/mapping/ans/ns')


def test_remove_mapping_fail_munged_auth():
    fail_munged_auth_delete('/api/v1/mapping/ans/ns')


def test_remove_mapping_fail_no_body():
    cli, _ = build_app()
    resp = cli.delete('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'})
    check_mapping_fail_no_body(resp)


def test_remove_mapping_fail_bad_json():
    cli, _ = build_app()
    resp = cli.delete('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                      data='{"foo": ["bar", "baz"}]')
    check_mapping_fail_bad_json(resp)


def test_remove_mapping_fail_not_dict():
    cli, _ = build_app()
    resp = cli.delete('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                      json=['foo', 'bar'])
    check_mapping_fail_not_dict(resp)


def test_remove_mapping_fail_missing_id():
    check_remove_mapping_fail_missing_id(None)
    check_remove_mapping_fail_missing_id([])


def check_remove_mapping_fail_missing_id(id_):
    cli, _ = build_app()
    resp = cli.delete('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                      json={'admin_id': id_})
    check_mapping_fail_missing_id(resp, 'admin_id')

    resp = cli.delete('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                      json={'other_id': id_, 'admin_id': 'id'})
    check_mapping_fail_missing_id(resp, 'other_id')


def test_remove_mapping_fail_whitespace_id():
    cli, _ = build_app()
    resp = cli.delete('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                      json={'admin_id': '    \t    '})
    check_mapping_fail_whitespace_id(resp, 'admin_id')

    resp = cli.delete('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                      json={'other_id': '    \t    ', 'admin_id': 'id'})
    check_mapping_fail_whitespace_id(resp, 'other_id')


def test_remove_mapping_fail_illegal_ns_id():
    fail_illegal_ns_id_delete('/api/v1/mapping/foo*bar/ns',
                              json={'admin_id': 'aid', 'other_id': 'id'})


def test_get_mappings_empty():
    check_get_mappings((set(), set()), {'admin': [], 'other': []})


def to_oid(namespace, id_):
    return(ObjectID(NamespaceID(namespace), id_))


def test_get_mappings_admin():
    check_get_mappings(
        (set([to_oid('ns3', 'id1'), to_oid('ns1', 'id3'), to_oid('ns1', 'id1'),
              to_oid('ns3', 'jd1')]),
         set()),
        {'admin': [{'namespace': 'ns1', 'id': 'id1'},
                   {'namespace': 'ns1', 'id': 'id3'},
                   {'namespace': 'ns3', 'id': 'id1'},
                   {'namespace': 'ns3', 'id': 'jd1'}],
         'other': []})


def test_get_mappings_other():
    check_get_mappings(
        (set(),
         set([to_oid('ns3', 'id1'), to_oid('ns1', 'id3'), to_oid('ns1', 'id1'),
              to_oid('ns3', 'jd1')])),
        {'admin': [],
         'other': [{'namespace': 'ns1', 'id': 'id1'},
                   {'namespace': 'ns1', 'id': 'id3'},
                   {'namespace': 'ns3', 'id': 'id1'},
                   {'namespace': 'ns3', 'id': 'jd1'}]})


def test_get_mappings_both():
    check_get_mappings(
        (set([to_oid('whee', 'myadiders'), to_oid('whoo', 'someid'), to_oid('baz', 'someid'),
              to_oid('whee', 'myadidas')]),
         set([to_oid('ns3', 'id1'), to_oid('ns1', 'id3'), to_oid('ns1', 'id1'),
              to_oid('ns3', 'jd1')])),
        {'admin': [{'namespace': 'baz', 'id': 'someid'},
                   {'namespace': 'whee', 'id': 'myadidas'},
                   {'namespace': 'whee', 'id': 'myadiders'},
                   {'namespace': 'whoo', 'id': 'someid'}],
         'other': [{'namespace': 'ns1', 'id': 'id1'},
                   {'namespace': 'ns1', 'id': 'id3'},
                   {'namespace': 'ns3', 'id': 'id1'},
                   {'namespace': 'ns3', 'id': 'jd1'}]})


def test_get_mappings_with_empty_filter():
    check_get_mappings(
        (set([to_oid('ns3', 'id1')]), set()),
        {'admin': [{'namespace': 'ns3', 'id': 'id1'}], 'other': []},
        ns_filter='?namespace_filter=   \t    ')


def test_get_mappings_with_filter():
    check_get_mappings(
        (set([to_oid('ns3', 'id1')]), set()),
        {'admin': [{'namespace': 'ns3', 'id': 'id1'}], 'other': []},
        ns_filter='?namespace_filter=   \t  ns3, ns1,  \t ns2   ',
        ns_filter_expected=[NamespaceID('ns3'), NamespaceID('ns1'), NamespaceID('ns2')])


def check_get_mappings(returned, expected, ns_filter='', ns_filter_expected=[]):
    cli, mapper = build_app()
    mapper.get_mappings.return_value = returned

    resp = cli.get('/api/v1/mapping/ns/id' + ns_filter)

    assert resp.get_json() == expected

    assert resp.status_code == 200

    assert mapper.get_mappings.call_args_list == [
        ((ObjectID(NamespaceID('ns'), 'id'), ns_filter_expected), {})]


def test_get_mappings_fail_whitespace_in_filter():
    cli, _ = build_app()

    resp = cli.get('/api/v1/mapping/ns/id?namespace_filter=ns1,    ,   ns2  , ns3')

    assert resp.get_json() == {
        'error': {'httpcode': 400,
                  'httpstatus': 'Bad Request',
                  'appcode': 30000,
                  'apperror': 'Missing input parameter',
                  'message': '30000 Missing input parameter: namespace id'
                  }
        }
    assert resp.status_code == 400


def test_get_mappings_fail_illegal_ns_id():
    fail_illegal_ns_id_get('/api/v1/mapping/foo*bar/aid')
    fail_illegal_ns_id_get('/api/v1/mapping/foobar/aid?namespace_filter=foo*bar')
