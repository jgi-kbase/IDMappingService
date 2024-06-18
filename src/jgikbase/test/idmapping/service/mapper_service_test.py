from unittest.mock import create_autospec, Mock
from jgikbase.idmapping.core.mapper import IDMapper
from jgikbase.idmapping.service.mapper_service import create_app, JSONFlaskLogFormatter
from jgikbase.idmapping.builder import IDMappingBuilder
from jgikbase.idmapping.core.object_id import Namespace, NamespaceID, ObjectID
from jgikbase.idmapping.core.user import AuthsourceID, User, Username
from jgikbase.idmapping.core.tokens import Token
from jgikbase.idmapping.core.errors import InvalidTokenError, NoSuchNamespaceError,\
    UnauthorizedError, NoSuchUserError
import re
from jgikbase.idmapping.service import mapper_service
from logging import LogRecord
import json
from flask.app import Flask
from flask import g
from typing import IO
from jgikbase.test.idmapping.test_utils import assert_ms_epoch_close_to_now, CALLID_PATTERN,\
    assert_json_error_correct

VERSION = '0.1.1'
WERKZEUG = 'werkzeug/0.16.0'


def build_app(ignore_ip_headers=False, logstream: IO[str]=None):
    builder = create_autospec(IDMappingBuilder, spec_set=True, instance=True)
    mapper = create_autospec(IDMapper, spec_set=True, instance=True)
    cfg = Mock()
    builder.build_id_mapping_system.return_value = mapper
    builder.get_cfg.return_value = cfg
    cfg.ignore_ip_headers = ignore_ip_headers

    app = create_app(builder, logstream)
    cli = app.test_client()

    return cli, mapper


def mock_request_for_ip_headers(remote_addr, xff, real_ip):
    req = Mock()
    req.headers.get.side_effect = [xff, real_ip]
    req.remote_addr = remote_addr
    return req


def test_get_ip_address_no_headers_with_ignore():
    req = mock_request_for_ip_headers('4.5.6.7', None, None)

    assert mapper_service.get_ip_address(req, True) == '4.5.6.7'
    assert req.headers.get.call_args_list == []


def test_get_ip_address_no_headers_no_ignore():
    req = mock_request_for_ip_headers('    \t  4.5.6.7    ', None, None)

    assert mapper_service.get_ip_address(req, False) == '4.5.6.7'
    assert req.headers.get.call_args_list == [(('X-Forwarded-For',), {}), (('X-Real-IP',), {})]


def test_get_ip_address_whitespace_headers_no_ignore():
    req = mock_request_for_ip_headers('4.5.6.7', '    \t    ', '    \t    ')

    assert mapper_service.get_ip_address(req, False) == '4.5.6.7'
    assert req.headers.get.call_args_list == [(('X-Forwarded-For',), {}), (('X-Real-IP',), {})]


def test_get_ip_address_with_headers_with_ignore():
    req = mock_request_for_ip_headers('4.5.6.7', '1.2.3.4, 5.6.7.8', '9.10.11.12')

    assert mapper_service.get_ip_address(req, True) == '4.5.6.7'
    assert req.headers.get.call_args_list == []


def test_get_ip_address_with_xff_and_real():
    req = mock_request_for_ip_headers('4.5.6.7', '   1.2.3.4    ,    5.6.7.8   ', '9.10.11.12')

    assert mapper_service.get_ip_address(req, False) == '1.2.3.4'
    assert req.headers.get.call_args_list == [(('X-Forwarded-For',), {}), (('X-Real-IP',), {})]


def test_get_ip_address_with_xff():
    req = mock_request_for_ip_headers('4.5.6.7', '1.2.3.4, 5.6.7.8', None)

    assert mapper_service.get_ip_address(req, False) == '1.2.3.4'
    assert req.headers.get.call_args_list == [(('X-Forwarded-For',), {}), (('X-Real-IP',), {})]


def test_get_ip_address_with_real():
    req = mock_request_for_ip_headers('4.5.6.7', None, '     9.10.11.12      ')

    assert mapper_service.get_ip_address(req, False) == '9.10.11.12'
    assert req.headers.get.call_args_list == [(('X-Forwarded-For',), {}), (('X-Real-IP',), {})]


def test_format_ip_headers_no_headers_with_ignore():
    req = mock_request_for_ip_headers('    \t  4.5.6.7    ', None, None)

    assert mapper_service.format_ip_headers(req, True) is None
    assert req.headers.get.call_args_list == []


def test_format_ip_headers_no_headers_no_ignore():
    req = mock_request_for_ip_headers('    \t  4.5.6.7    ', None, None)

    assert mapper_service.format_ip_headers(req, False) is None
    assert req.headers.get.call_args_list == [(('X-Forwarded-For',), {}), (('X-Real-IP',), {})]


def test_format_ip_headers_whitespace_headers_no_ignore():
    req = mock_request_for_ip_headers('    \t  4.5.6.7    ', '    \t    ', '    \t    ')

    assert mapper_service.format_ip_headers(req, False) is None
    assert req.headers.get.call_args_list == [(('X-Forwarded-For',), {}), (('X-Real-IP',), {})]


def test_format_ip_headers_with_headers_with_ignore():
    req = mock_request_for_ip_headers('4.5.6.7', '1.2.3.4, 5.6.7.8', '9.10.11.12')

    assert mapper_service.format_ip_headers(req, True) is None
    assert req.headers.get.call_args_list == []


def test_format_ip_headers_with_xff_and_real():
    req = mock_request_for_ip_headers('   4.5.6.7  \t ', '   1.2.3.4    ,    5.6.7.8   ',
                                      '    9.10.11.12  \t  ')

    assert mapper_service.format_ip_headers(req, False) == (
        'X-Forwarded-For: 1.2.3.4    ,    5.6.7.8, X-Real-IP: 9.10.11.12, Remote IP: 4.5.6.7')
    assert req.headers.get.call_args_list == [(('X-Forwarded-For',), {}), (('X-Real-IP',), {})]


def test_format_ip_headers_with_xff():
    req = mock_request_for_ip_headers('   4.5.6.7  \t ', '   1.2.3.4    ,    5.6.7.8   ', None)

    assert mapper_service.format_ip_headers(req, False) == (
        'X-Forwarded-For: 1.2.3.4    ,    5.6.7.8, Remote IP: 4.5.6.7')
    assert req.headers.get.call_args_list == [(('X-Forwarded-For',), {}), (('X-Real-IP',), {})]


def test_format_ip_headers_with_real():
    req = mock_request_for_ip_headers('   4.5.6.7  \t ', None, '    9.10.11.12  \t  ')

    assert mapper_service.format_ip_headers(req, False) == (
        'X-Real-IP: 9.10.11.12, Remote IP: 4.5.6.7')
    assert req.headers.get.call_args_list == [(('X-Forwarded-For',), {}), (('X-Real-IP',), {})]


def test_log_formatter_no_exception():
    app = Flask('foo')
    f = JSONFlaskLogFormatter('service name')
    with app.test_request_context('/'):
        g.ip = '4.5.6.7'
        g.method = 'POST'
        g.req_id = '1564161'
        format1 = f.format(LogRecord('my name', 40, 'path', 2, '%s foo %s', ('bar', 'baz'),
                                     None, None, None))
        format2 = f.format(LogRecord('my name', 40, 'path', 2, '%s foo %s', ('bar', 'baz'),
                                     (None, None, None), None, None))
    contents1 = json.loads(format1)
    contents2 = json.loads(format2)
    time1 = contents1['time']
    del contents1['time']
    time2 = contents2['time']
    del contents2['time']

    expected = {
        'service': 'service name',
        'level': 'ERROR',
        'source': 'my name',
        'ip': '4.5.6.7',
        'method': 'POST',
        'callid': '1564161',
        'msg': 'bar foo baz'
        }

    assert contents1 == expected
    assert contents2 == expected

    assert_ms_epoch_close_to_now(time1)
    assert_ms_epoch_close_to_now(time2)


def test_log_formatter_with_exception():
    app = Flask('foo')
    f = JSONFlaskLogFormatter('service name')

    def exception_method():
        raise NoSuchUserError('userfoo')

    try:
        exception_method()
    except Exception as err:
        e = err
    exc_info = (type(e), e, e.__traceback__)
    with app.test_request_context('/'):
        g.ip = '4.5.6.7'
        g.method = 'POST'
        g.req_id = '1564161'
        format_ = f.format(LogRecord('my name', 40, 'path', 2, '%s foo %s', ('bar', 'baz'),
                                     exc_info, None, None))
    contents = json.loads(format_)
    time_ = contents['time']
    del contents['time']
    excep = contents['excep']
    del contents['excep']

    print(contents)
    assert contents == {
        'service': 'service name',
        'level': 'ERROR',
        'source': 'my name',
        'ip': '4.5.6.7',
        'method': 'POST',
        'callid': '1564161',
        'msg': 'bar foo baz'
        }

    assert_ms_epoch_close_to_now(time_)

    assert 'exception_method()' in excep
    assert 'NoSuchUserError: 50000 No such user: userfoo' in excep
    assert 'Traceback (most' in excep


def test_root_and_logging():
    # Also tests basic logging
    logstream = Mock()
    cli, _ = build_app(logstream=logstream)

    resp = cli.get('/')
    j = resp.get_json()

    time_ = j['servertime']
    commit = j['gitcommithash']
    del j['servertime']
    del j['gitcommithash']

    assert j == {'service': 'ID Mapping Service', 'version': VERSION}
    assert re.match('[a-f\d]{40}', commit) is not None
    assert_ms_epoch_close_to_now(time_)
    assert resp.status_code == 200

    assert len(logstream.write.call_args_list) == 1
    # print("--------")
    # print(logstream.write.call_args_list)
    # print("--------")
    # print(logstream.write.call_args_list[0])
    # print("--------")
    # print(logstream.write.call_args_list[0][0])
    # print("--------")
    # print(logstream.write.call_args_list[0][0][0])
    # print("--------")
    assert logstream.write.call_args_list[0][0][0][-1] == '\n'
    logjson = json.loads(logstream.write.call_args_list[0][0][0])

    time_ = logjson['time']
    del logjson['time']
    callid = logjson['callid']
    del logjson['callid']

    assert logjson == {'service': 'IDMappingService',
                       'level': 'INFO',
                       'source': 'jgikbase.idmapping.service.mapper_service',
                       'ip': '127.0.0.1',
                       'method': 'GET',
                       'msg': f'GET / 200 {WERKZEUG}'}
    assert_ms_epoch_close_to_now(time_)
    assert CALLID_PATTERN.match(callid) is not None


def test_root_and_logging_with_xff_and_real_headers():
    logstream = Mock()
    cli, _ = build_app(logstream=logstream)

    cli.get('/', headers={'x-forwarded-for': '    1.2.3.4,    5.6.7.8   ',
                          'x-real-ip': '   7.8.9.10    '})  # already tested response, don't care

    assert len(logstream.write.call_args_list) == 4
    assert logstream.write.call_args_list[1][0][0] == '\n'
    assert logstream.write.call_args_list[3][0][0] == '\n'
    ipjson = json.loads(logstream.write.call_args_list[0][0][0])
    respjson = json.loads(logstream.write.call_args_list[2][0][0])

    # don't check these again, checked above.
    del ipjson['time']
    del respjson['time']
    del ipjson['callid']
    del respjson['callid']

    assert ipjson == {
        'service': 'IDMappingService',
        'level': 'INFO',
        'source': 'jgikbase.idmapping.service.mapper_service',
        'ip': '1.2.3.4',
        'method': 'GET',
        'msg': 'X-Forwarded-For: 1.2.3.4,    5.6.7.8, X-Real-IP: 7.8.9.10, Remote IP: 127.0.0.1'}

    assert respjson == {'service': 'IDMappingService',
                        'level': 'INFO',
                        'source': 'jgikbase.idmapping.service.mapper_service',
                        'ip': '1.2.3.4',
                        'method': 'GET',
                        'msg': f'GET / 200 {WERKZEUG}'}


def test_root_and_logging_with_xff_and_real_headers_ignored():
    logstream = Mock()
    cli, _ = build_app(logstream=logstream, ignore_ip_headers=True)

    cli.get('/', headers={'x-forwarded-for': '    1.2.3.4,    5.6.7.8   ',
                          'x-real-ip': '   7.8.9.10    '})  # already tested response, don't care

    assert len(logstream.write.call_args_list) == 2
    assert logstream.write.call_args_list[1][0][0] == '\n'
    respjson = json.loads(logstream.write.call_args_list[0][0][0])

    # don't check these again, checked above.
    del respjson['time']
    del respjson['callid']

    assert respjson == {'service': 'IDMappingService',
                        'level': 'INFO',
                        'source': 'jgikbase.idmapping.service.mapper_service',
                        'ip': '127.0.0.1',
                        'method': 'GET',
                        'msg': f'GET / 200 {WERKZEUG}'}


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
    # general tests of the application error handler for general application errors
    logstream = Mock()
    cli, _ = build_app(logstream=logstream)
    resp = cli.get('/api/v1/namespace/foo', headers={'Authorization': 'astoketoketoke'})

    err = '30001 Illegal input parameter: Expected authsource and token in header.'
    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 400,
                   'httpstatus': 'Bad Request',
                   'appcode': 30001,
                   'apperror': 'Illegal input parameter',
                   'message': err
                   }
         })
    assert resp.status_code == 400
    check_error_logging(logstream, 'GET', '/api/v1/namespace/foo', 400,
                        'IllegalParameterError: ' + err)


def test_get_namespace_fail_invalid_token():
    # really a general test of the authentication error handler
    logstream = Mock()
    cli, mapper = build_app(logstream=logstream)
    mapper.get_namespace.side_effect = InvalidTokenError()

    resp = cli.get('/api/v1/namespace/foo', headers={'Authorization': 'as toketoketoke'})

    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 401,
                   'httpstatus': 'Unauthorized',
                   'appcode': 10020,
                   'apperror': 'Invalid token',
                   'message': '10020 Invalid token'
                   }
         })
    assert resp.status_code == 401
    check_error_logging(logstream, 'GET', '/api/v1/namespace/foo', 401,
                        'InvalidTokenError: 10020 Invalid token')


def check_error_logging(logstream_mock, method, url, code, stackstring):

    assert len(logstream_mock.write.call_args_list) == 4
    assert logstream_mock.write.call_args_list[1][0][0] == '\n'
    assert logstream_mock.write.call_args_list[3][0][0] == '\n'
    errjson = json.loads(logstream_mock.write.call_args_list[0][0][0])
    respjson = json.loads(logstream_mock.write.call_args_list[2][0][0])

    errtime = errjson['time']
    del errjson['time']
    errcallid = errjson['callid']
    del errjson['callid']

    resptime = respjson['time']
    del respjson['time']
    respcallid = respjson['callid']
    del respjson['callid']

    stack = errjson['msg']
    del errjson['msg']

    assert errjson == {
        'service': 'IDMappingService',
        'level': 'ERROR',
        'source': 'jgikbase.idmapping.service.mapper_service',
        'ip': '127.0.0.1',
        'method': method}

    assert stack.startswith('Logging exception:\n')
    assert 'Traceback (most' in stack
    assert stackstring in stack

    assert respjson == {'service': 'IDMappingService',
                        'level': 'INFO',
                        'source': 'jgikbase.idmapping.service.mapper_service',
                        'ip': '127.0.0.1',
                        'method': method,
                        'msg': '{} {} {} {}'.format(method, url, code, WERKZEUG)}
    assert_ms_epoch_close_to_now(errtime)
    assert CALLID_PATTERN.match(errcallid) is not None
    assert_ms_epoch_close_to_now(resptime)
    assert CALLID_PATTERN.match(respcallid) is not None


def test_get_namespace_fail_no_namespace():
    # really a general test of the no data error handler
    logstream = Mock()
    cli, mapper = build_app(logstream=logstream)
    mapper.get_namespace.side_effect = NoSuchNamespaceError('foo')

    resp = cli.get('/api/v1/namespace/foo')

    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 404,
                   'httpstatus': 'Not Found',
                   'appcode': 50010,
                   'apperror': 'No such namespace',
                   'message': '50010 No such namespace: foo'
                   }
         })
    assert resp.status_code == 404

    check_error_logging(logstream, 'GET', '/api/v1/namespace/foo', 404,
                        'NoSuchNamespaceError: 50010 No such namespace: foo')


def test_get_namespace_fail_valueerror():
    # really a general test of the catch all error handler
    logstream = Mock()
    cli, mapper = build_app(logstream=logstream)
    mapper.get_namespace.side_effect = ValueError('things are all messed up down here')

    resp = cli.get('/api/v1/namespace/foo')

    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 500,
                   'httpstatus': 'Internal Server Error',
                   'message': 'things are all messed up down here'
                   }
         })
    assert resp.status_code == 500

    check_error_logging(logstream, 'GET', '/api/v1/namespace/foo', 500,
                        'ValueError: things are all messed up down here')


def test_method_not_allowed():
    logstream = Mock()
    cli, _ = build_app(logstream=logstream)

    resp = cli.delete('/api/v1/namespace/foo')

    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 405,
                   'httpstatus': 'Method Not Allowed',
                   'message': ('405 Method Not Allowed: The method is not allowed ' +
                               'for the requested URL.')
                   }
         })
    assert resp.status_code == 405

    check_error_logging(logstream, 'DELETE', '/api/v1/namespace/foo', 405,
                        'MethodNotAllowed: 405 Method Not Allowed: The method is not allowed ' +
                        'for the requested URL.')


def test_not_found():
    logstream = Mock()
    cli, _ = build_app(logstream=logstream)

    resp = cli.get('/api/v1/nothinghere')

    err = ('404 Not Found: The requested URL was not found on the server. ' +
           'If you entered the URL manually please check your spelling and try again.')
    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 404,
                   'httpstatus': 'Not Found',
                   'message': err
                   }
         })
    assert resp.status_code == 404

    check_error_logging(logstream, 'GET', '/api/v1/nothinghere', 404,
                        'NotFound: ' + err)


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
    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 401,
                   'appcode': 10010,
                   'apperror': 'No authentication token',
                   'httpstatus': 'Unauthorized',
                   'message': '10010 No authentication token'
                   }
         })
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
    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 400,
                   'httpstatus': 'Bad Request',
                   'appcode': 30001,
                   'apperror': 'Illegal input parameter',
                   'message': ('30001 Illegal input parameter: ' +
                               'Expected authsource and token in header.')
                   }
         })
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
    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 400,
                   'httpstatus': 'Bad Request',
                   'appcode': 30001,
                   'apperror': 'Illegal input parameter',
                   'message': ('30001 Illegal input parameter: ' +
                               'Illegal character in namespace id foo*bar: *')
                   }
         })
    assert resp.status_code == 400


def test_create_namespace_fail_unauthorized():
    # general test of the unauthorized error handler
    logstream = Mock()
    cli, mapper = build_app(logstream=logstream)

    mapper.create_namespace.side_effect = UnauthorizedError('YOU SHALL NOT PASS')

    resp = cli.put('/api/v1/namespace/foo', headers={'Authorization': 'source tokey'})

    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 403,
                   'httpstatus': 'Forbidden',
                   'appcode': 20000,
                   'apperror': 'Unauthorized',
                   'message': '20000 Unauthorized: YOU SHALL NOT PASS'
                   }
         })
    assert resp.status_code == 403

    assert mapper.create_namespace.call_args_list == [((
        AuthsourceID('source'), Token('tokey'), NamespaceID('foo')), {})]

    check_error_logging(logstream, 'PUT', '/api/v1/namespace/foo', 403,
                        'UnauthorizedError: 20000 Unauthorized: YOU SHALL NOT PASS')


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


def test_set_namespace_fail_no_op():
    cli, _ = build_app()

    resp = cli.put('/api/v1/namespace/foo/set', headers={'Authorization': 'source tokey'})

    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 400,
                   'httpstatus': 'Bad Request',
                   'appcode': 30000,
                   'apperror': 'Missing input parameter',
                   'message': '30000 Missing input parameter: No settings provided.'
                   }
         })
    assert resp.status_code == 400


def test_set_namespace_publicly_mappable_illegal_input():
    cli, _ = build_app()

    resp = cli.put('/api/v1/namespace/foo/set?publicly_mappable=foobar',
                   headers={'Authorization': 'source tokey'})

    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 400,
                   'httpstatus': 'Bad Request',
                   'appcode': 30001,
                   'apperror': 'Illegal input parameter',
                   'message': ("30001 Illegal input parameter: Expected value of 'true' or " +
                               "'false' for publicly_mappable")
                   }
         })
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
    resp = cli.put('/api/v1/mapping/ans/ns',
                   headers={'Authorization': 'source tokey',
                            'content-type': 'x-www-form-urlencoded'},
                   data='{"aid1": "id1", "id2": "id2"}')
    check_create_mapping(resp, mapper)


def test_create_mapping_post():
    cli, mapper = build_app()
    resp = cli.post('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                    json={'    aid1    \t   ': 'id1', 'id2': '    \t   id2   '})
    check_create_mapping(resp, mapper)


def check_create_mapping(resp, mapper):
    assert resp.data == b''
    assert resp.status_code == 204

    assert mapper.create_mapping.call_args_list == [
        ((AuthsourceID('source'), Token('tokey'),
          ObjectID(NamespaceID('ans'), 'aid1'),
          ObjectID(NamespaceID('ns'), 'id1')), {}),
        ((AuthsourceID('source'), Token('tokey'),
          ObjectID(NamespaceID('ans'), 'id2'),
          ObjectID(NamespaceID('ns'), 'id2')), {})]


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
    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 400,
                   'httpstatus': 'Bad Request',
                   'message': 'Input JSON decode error: Expecting value: line 1 column 1 (char 0)'
                   }
         })
    assert resp.status_code == 400


def test_bad_json_error():
    logstream = Mock()
    cli, _ = build_app(logstream=logstream)
    resp = cli.put('/api/v1/mapping/ans/ns',  headers={'Authorization': 'source tokey'},
                   data='{"foo": ["bar", "baz"}]')

    err = "Expecting ',' delimiter: line 1 column 22 (char 21)"
    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 400,
                   'httpstatus': 'Bad Request',
                   'message': 'Input JSON decode error: ' + err
                   }
         })
    assert resp.status_code == 400
    check_error_logging(logstream, 'PUT', '/api/v1/mapping/ans/ns', 400, 'JSONDecodeError: ' + err)


def test_create_mapping_fail_bad_json():
    cli, _ = build_app()
    resp = cli.put('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                   data='{"foo": ["bar", "baz"}]')
    check_mapping_fail_bad_json(resp)


def check_mapping_fail_bad_json(resp):
    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 400,
                   'httpstatus': 'Bad Request',
                   'message': ("Input JSON decode error: Expecting ',' delimiter: " +
                               "line 1 column 22 (char 21)")
                   }
         })
    assert resp.status_code == 400


def test_create_mapping_fail_not_dict():
    cli, _ = build_app()
    resp = cli.put('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                   json=['foo', 'bar'])
    check_mapping_fail_not_dict(resp)


def check_mapping_fail_not_dict(resp):
    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 400,
                   'httpstatus': 'Bad Request',
                   'appcode': 30001,
                   'apperror': 'Illegal input parameter',
                   'message': ('30001 Illegal input parameter: ' +
                               'Expected JSON mapping in request body')
                   }
         })
    assert resp.status_code == 400


def test_create_mapping_fail_no_ids():
    cli, _ = build_app()
    resp = cli.put('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                   json={})
    check_mapping_fail_no_ids(resp)


def check_mapping_fail_no_ids(resp):
    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 400,
                   'httpstatus': 'Bad Request',
                   'appcode': 30000,
                   'apperror': 'Missing input parameter',
                   'message': '30000 Missing input parameter: No ids supplied'
                   }
         })
    assert resp.status_code == 400


def test_create_mapping_fail_whitespace_key():
    cli, _ = build_app()
    resp = cli.put('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                   json={'   \t   ': 'id1'})
    check_mapping_fail_whitespace_key(resp)


def check_mapping_fail_whitespace_key(resp):
    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 400,
                   'httpstatus': 'Bad Request',
                   'appcode': 30000,
                   'apperror': 'Missing input parameter',
                   'message': '30000 Missing input parameter: whitespace only key in input JSON'
                   }
         })
    assert resp.status_code == 400


def test_create_mapping_fail_non_string_value():
    cli, _ = build_app()
    resp = cli.put('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                   json={'id': []})
    check_mapping_fail_non_string_value(resp)


def check_mapping_fail_non_string_value(resp):
    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 400,
                   'httpstatus': 'Bad Request',
                   'appcode': 30001,
                   'apperror': 'Illegal input parameter',
                   'message': ('30001 Illegal input parameter: ' +
                               'value for key id in input JSON is not string: []')
                   }
         })
    assert resp.status_code == 400


def test_create_mapping_fail_whitespace_value():
    cli, _ = build_app()
    resp = cli.put('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                   json={'id': '    \t    '})
    check_mapping_fail_whitespace_value(resp)


def check_mapping_fail_whitespace_value(resp):
    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 400,
                   'httpstatus': 'Bad Request',
                   'appcode': 30000,
                   'apperror': 'Missing input parameter',
                   'message': ('30000 Missing input parameter: ' +
                               'value for key id in input JSON is whitespace only')
                   }
         })
    assert resp.status_code == 400


def test_create_mapping_fail_too_many_ids():
    cli, _ = build_app()
    resp = cli.put('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                   json={str(x): str(x) for x in range(10001)})
    check_mapping_fail_too_many_ids(resp)


def check_mapping_fail_too_many_ids(resp):
    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 400,
                   'httpstatus': 'Bad Request',
                   'appcode': 30001,
                   'apperror': 'Illegal input parameter',
                   'message': ('30001 Illegal input parameter: ' +
                               'A maximum of 10000 ids are allowed')
                   }
         })
    assert resp.status_code == 400


def test_create_mapping_fail_illegal_ns_id():
    fail_illegal_ns_id_put('/api/v1/mapping/foo*bar/ns',
                           json={'admin_id': 'aid', 'other_id': 'id'})


def test_remove_mapping():
    cli, mapper = build_app()

    resp = cli.delete('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                      json={'   some id   ': 'aid', 'other_id': '    \t   id    '})

    assert resp.data == b''
    assert resp.status_code == 204

    assert mapper.remove_mapping.call_args_list == [
        ((AuthsourceID('source'), Token('tokey'),
          ObjectID(NamespaceID('ans'), 'some id'),
          ObjectID(NamespaceID('ns'), 'aid')), {}),
        ((AuthsourceID('source'), Token('tokey'),
          ObjectID(NamespaceID('ans'), 'other_id'),
          ObjectID(NamespaceID('ns'), 'id')), {})
        ]


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


def test_remove_mapping_fail_no_ids():
    cli, _ = build_app()
    resp = cli.delete('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                      json={})
    check_mapping_fail_no_ids(resp)


def test_remove_mapping_fail_whitespace_key():
    cli, _ = build_app()
    resp = cli.delete('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                      json={'   \t   ': 'id1'})
    check_mapping_fail_whitespace_key(resp)


def test_remove_mapping_fail_non_string_value():
    cli, _ = build_app()
    resp = cli.delete('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                      json={'id': []})
    check_mapping_fail_non_string_value(resp)


def test_remove_mapping_fail_whitespace_value():
    cli, _ = build_app()
    resp = cli.delete('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                      json={'id': '    \t    '})
    check_mapping_fail_whitespace_value(resp)


def test_remove_mapping_fail_too_many_ids():
    cli, _ = build_app()
    resp = cli.delete('/api/v1/mapping/ans/ns', headers={'Authorization': 'source tokey'},
                      json={str(x): str(x) for x in range(10001)})
    check_mapping_fail_too_many_ids(resp)


def test_remove_mapping_fail_illegal_ns_id():
    fail_illegal_ns_id_delete('/api/v1/mapping/foo*bar/ns',
                              json={'admin_id': 'aid', 'other_id': 'id'})


def test_get_mappings_empty():
    check_get_mappings([(set(), set()), (set(), set())],
                       {'id1': {'mappings': []}, 'id2': {'mappings': []}})
    check_get_mappings([(set(), set()), (set(), set())],
                       {'id1': {'admin': [], 'other': []}, 'id2': {'admin': [], 'other': []}},
                       query='?separate')


def to_oid(namespace, id_):
    return(ObjectID(NamespaceID(namespace), id_))


def test_get_mappings_admin():
    check_get_mappings(
        [(set([to_oid('ns3', 'id1'), to_oid('ns1', 'id3'), to_oid('ns1', 'id1'),
               to_oid('ns3', 'jd1')]),
          set()),
         (set([to_oid('ns', 'id')]),
          set())],
        {'id1': {'mappings': [{'ns': 'ns1', 'id': 'id1'},
                              {'ns': 'ns1', 'id': 'id3'},
                              {'ns': 'ns3', 'id': 'id1'},
                              {'ns': 'ns3', 'id': 'jd1'}]
                 },
         'id2': {'mappings': [{'ns': 'ns', 'id': 'id'}]}
         })

    check_get_mappings(
        [(set([to_oid('ns3', 'id1'), to_oid('ns1', 'id3'), to_oid('ns1', 'id1'),
               to_oid('ns3', 'jd1')]),
          set()),
         (set([to_oid('ns', 'id')]),
          set())],
        {'id1': {'admin': [{'ns': 'ns1', 'id': 'id1'},
                           {'ns': 'ns1', 'id': 'id3'},
                           {'ns': 'ns3', 'id': 'id1'},
                           {'ns': 'ns3', 'id': 'jd1'}],
                 'other': []
                 },
         'id2': {'admin': [{'ns': 'ns', 'id': 'id'}],
                 'other': []
                 }
         },
        query='?separate')


def test_get_mappings_other():
    check_get_mappings(
        [(set(),
          set([to_oid('ns3', 'id1'), to_oid('ns1', 'id3'), to_oid('ns1', 'id1'),
               to_oid('ns3', 'jd1')])),
         (set(),
          set([to_oid('ns', 'id')]))],
        {'id1': {'mappings': [{'ns': 'ns1', 'id': 'id1'},
                              {'ns': 'ns1', 'id': 'id3'},
                              {'ns': 'ns3', 'id': 'id1'},
                              {'ns': 'ns3', 'id': 'jd1'}]
                 },
         'id2': {'mappings': [{'ns': 'ns', 'id': 'id'}]}
         })

    check_get_mappings(
        [(set(),
          set([to_oid('ns3', 'id1'), to_oid('ns1', 'id3'), to_oid('ns1', 'id1'),
               to_oid('ns3', 'jd1')])),
         (set(),
          set([to_oid('ns', 'id')]))],
        {'id1': {'admin': [],
                 'other': [{'ns': 'ns1', 'id': 'id1'},
                           {'ns': 'ns1', 'id': 'id3'},
                           {'ns': 'ns3', 'id': 'id1'},
                           {'ns': 'ns3', 'id': 'jd1'}]
                 },
         'id2': {'admin': [],
                 'other': [{'ns': 'ns', 'id': 'id'}]
                 }
         },
        query='?separate')


def test_get_mappings_both():
    check_get_mappings(
        [(set([to_oid('whee', 'myadiders'), to_oid('whoo', 'someid'), to_oid('baz', 'someid'),
              to_oid('whee', 'myadidas')]),
         set([to_oid('ns3', 'id1'), to_oid('ns1', 'id3'), to_oid('ns1', 'id1'),
              to_oid('ns3', 'jd1')])),
         (set([to_oid('ns', 'id')]),
          set())],
        {'id1': {'mappings': [{'ns': 'baz', 'id': 'someid'},
                              {'ns': 'ns1', 'id': 'id1'},
                              {'ns': 'ns1', 'id': 'id3'},
                              {'ns': 'ns3', 'id': 'id1'},
                              {'ns': 'ns3', 'id': 'jd1'},
                              {'ns': 'whee', 'id': 'myadidas'},
                              {'ns': 'whee', 'id': 'myadiders'},
                              {'ns': 'whoo', 'id': 'someid'}]
                 },
         'id2': {'mappings': [{'ns': 'ns', 'id': 'id'}]}
         })

    check_get_mappings(
        [(set([to_oid('whee', 'myadiders'), to_oid('whoo', 'someid'), to_oid('baz', 'someid'),
              to_oid('whee', 'myadidas')]),
         set([to_oid('ns3', 'id1'), to_oid('ns1', 'id3'), to_oid('ns1', 'id1'),
              to_oid('ns3', 'jd1')])),
         (set([to_oid('ns', 'id')]),
          set())],
        {'id1': {'admin': [{'ns': 'baz', 'id': 'someid'},
                           {'ns': 'whee', 'id': 'myadidas'},
                           {'ns': 'whee', 'id': 'myadiders'},
                           {'ns': 'whoo', 'id': 'someid'}],
                 'other': [{'ns': 'ns1', 'id': 'id1'},
                           {'ns': 'ns1', 'id': 'id3'},
                           {'ns': 'ns3', 'id': 'id1'},
                           {'ns': 'ns3', 'id': 'jd1'}]
                 },
         'id2': {'admin': [{'ns': 'ns', 'id': 'id'}],
                 'other': []
                 }
         },
        query='?separate')


def test_get_mappings_with_empty_filter():
    check_get_mappings(
        [(set([to_oid('ns3', 'id1')]), set()), (set(), set())],
        {'id1': {'mappings': [{'ns': 'ns3', 'id': 'id1'}]}, 'id2': {'mappings': []}},
        query='?namespace_filter=   \t    ')

    check_get_mappings(
        [(set([to_oid('ns3', 'id1')]), set()), (set(), set())],
        {'id1': {'admin': [{'ns': 'ns3', 'id': 'id1'}], 'other': []},
         'id2': {'admin': [], 'other': []}},
        query='?separate&namespace_filter=   \t    ')


def test_get_mappings_with_filter():
    check_get_mappings(
        [(set([to_oid('ns3', 'id1')]), set()), (set(), set())],
        {'id1': {'mappings': [{'ns': 'ns3', 'id': 'id1'}]}, 'id2': {'mappings': []}},
        query='?namespace_filter=   \t  ns3, ns1,  \t ns2   ',
        ns_filter_expected=[NamespaceID('ns3'), NamespaceID('ns1'), NamespaceID('ns2')])

    check_get_mappings(
        [(set([to_oid('ns3', 'id1')]), set()), (set(), set())],
        {'id1': {'admin': [{'ns': 'ns3', 'id': 'id1'}], 'other': []},
         'id2': {'admin': [], 'other': []}},
        query='?separate&namespace_filter=   \t  ns3, ns1,  \t ns2   ',
        ns_filter_expected=[NamespaceID('ns3'), NamespaceID('ns1'), NamespaceID('ns2')])


def check_get_mappings(returned, expected, query='', ns_filter_expected=[]):
    cli, mapper = build_app()
    mapper.get_mappings.side_effect = returned

    resp = cli.get('/api/v1/mapping/ns' + query, json={'ids': ['   id1   \t', 'id2']})

    assert resp.get_json() == expected

    assert resp.status_code == 200

    assert mapper.get_mappings.call_args_list == [
        ((ObjectID(NamespaceID('ns'), 'id1'), ns_filter_expected), {}),
        ((ObjectID(NamespaceID('ns'), 'id2'), ns_filter_expected), {})]


def test_get_mappings_fail_no_body():
    cli, _ = build_app()

    resp = cli.get('/api/v1/mapping/ns')
    check_mapping_fail_no_body(resp)


def test_get_mapping_fail_bad_json():
    cli, _ = build_app()
    resp = cli.get('/api/v1/mapping/ans', data='{"foo": ["bar", "baz"}]')
    check_mapping_fail_bad_json(resp)


def test_get_mapping_fail_not_dict():
    cli, _ = build_app()
    resp = cli.get('/api/v1/mapping/ans', json=['foo', 'bar'])
    check_mapping_fail_not_dict(resp)


def test_get_mapping_fail_ids_not_list():
    cli, _ = build_app()
    resp = cli.get('/api/v1/mapping/ans', json={'ids': {'id': 'id'}})

    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 400,
                   'httpstatus': 'Bad Request',
                   'appcode': 30001,
                   'apperror': 'Illegal input parameter',
                   'message': ('30001 Illegal input parameter: ' +
                               'Expected list at /ids in request body')
                   }
         })
    assert resp.status_code == 400


def test_get_mapping_fail_ids_empty():
    cli, _ = build_app()
    resp = cli.get('/api/v1/mapping/ans', json={'ids': []})

    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 400,
                   'httpstatus': 'Bad Request',
                   'appcode': 30000,
                   'apperror': 'Missing input parameter',
                   'message': '30000 Missing input parameter: No ids supplied'
                   }
         })
    assert resp.status_code == 400


def test_get_mapping_fail_bad_id():
    cli, _ = build_app()
    resp = cli.get('/api/v1/mapping/ans', json={'ids': ['id', None, 'id1']})
    check_get_mapping_fail_bad_id(resp)

    resp = cli.get('/api/v1/mapping/ans', json={'ids': ['id', '   \t    ', 'id1']})
    check_get_mapping_fail_bad_id(resp)


def check_get_mapping_fail_bad_id(resp):
    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 400,
                   'httpstatus': 'Bad Request',
                   'appcode': 30000,
                   'apperror': 'Missing input parameter',
                   'message': '30000 Missing input parameter: null or whitespace-only id in list'
                   }
         })
    assert resp.status_code == 400


def test_get_mapping_fail_too_many_ids():
    cli, _ = build_app()
    resp = cli.get('/api/v1/mapping/ans', json={'ids': [str(x) for x in range(1001)]})

    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 400,
                   'httpstatus': 'Bad Request',
                   'appcode': 30001,
                   'apperror': 'Illegal input parameter',
                   'message': ('30001 Illegal input parameter: ' +
                               'A maximum of 1000 ids are allowed')
                   }
         })
    assert resp.status_code == 400


def test_get_mappings_fail_whitespace_in_filter():
    cli, _ = build_app()

    resp = cli.get('/api/v1/mapping/ns?namespace_filter=ns1,    ,   ns2  , ns3')

    assert_json_error_correct(
        resp.get_json(),
        {'error': {'httpcode': 400,
                   'httpstatus': 'Bad Request',
                   'appcode': 30000,
                   'apperror': 'Missing input parameter',
                   'message': '30000 Missing input parameter: namespace id'
                   }
         })
    assert resp.status_code == 400


def test_get_mappings_fail_illegal_ns_id():
    fail_illegal_ns_id_get('/api/v1/mapping/foo*bar', json={'ids': ['id']})
    fail_illegal_ns_id_get('/api/v1/mapping/foobar?namespace_filter=foo*bar', json={'ids': ['id']})
