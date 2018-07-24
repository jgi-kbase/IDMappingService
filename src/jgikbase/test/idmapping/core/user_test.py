from jgikbase.idmapping.core.user import AuthsourceID, User, LOCAL
from pytest import fail
from jgikbase.test.idmapping.test_utils import assert_exception_correct
from jgikbase.idmapping.core.errors import IllegalUsernameError, MissingParameterError,\
    IllegalParameterError

LONG_STR = 'a' * 100


def test_authsource_init_pass():
    as_ = AuthsourceID('abcdefghijklmnopqrst')
    assert as_.id == 'abcdefghijklmnopqrst'

    as_ = AuthsourceID('uvwxyz')
    assert as_.id == 'uvwxyz'


def test_authsource_init_fail():
    fail_authsource_init(None, MissingParameterError('authsource id'))
    fail_authsource_init('   \t    \n   ',
                         MissingParameterError('authsource id'))
    fail_authsource_init('abcdefghijklmnopqrstu', IllegalParameterError(
        'authsource id abcdefghijklmnopqrstu exceeds maximum length of 20'))
    fail_authsource_init('fooo1b&',
                         IllegalParameterError('Illegal character in authsource id fooo1b&: 1'))


def fail_authsource_init(source: str, expected: Exception):
    try:
        AuthsourceID(source)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)


def test_authsource_equals():
    assert AuthsourceID('foo') == AuthsourceID('foo')
    assert AuthsourceID('foo') != AuthsourceID('bar')
    assert AuthsourceID('foo') != LOCAL
    assert AuthsourceID('local') == LOCAL
    assert LOCAL == LOCAL
    assert AuthsourceID('foo') != 'foo'


def test_user_init_pass():
    u = User(AuthsourceID('foo'), LONG_STR[0:64] + 'abcdefghijklmnopqrstuvwxyz0123456789')
    # yuck, but don't want to add a hash fn to authsource unless necessary
    assert u.authsource_id == AuthsourceID('foo')
    assert u.username == LONG_STR[0:64] + 'abcdefghijklmnopqrstuvwxyz0123456789'


def test_user_init_fail():
    as_ = AuthsourceID('bar')
    fail_user_init(None, 'foo', MissingParameterError('authsource_id'))
    fail_user_init(as_, None, MissingParameterError('username'))
    fail_user_init(as_, '       \t      \n   ', MissingParameterError('username'))
    fail_user_init(as_, LONG_STR + 'b', IllegalUsernameError(
        'username ' + LONG_STR + 'b exceeds maximum length of 100'))
    for c in '0123456789':
        fail_user_init(as_, c + 'foo',
                       IllegalUsernameError('username ' + c + 'foo must start with a letter'))
    for c in '*&@-+\n\t~_':
        fail_user_init(as_, 'foo1d' + c,
                       IllegalUsernameError('Illegal character in username foo1d' + c + ': ' + c))


def fail_user_init(authsource: AuthsourceID, username: str, expected: Exception):
    try:
        User(authsource, username)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)
