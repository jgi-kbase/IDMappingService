from jgikbase.idmapping.core.user import AuthsourceID, User, LOCAL
from pytest import fail
from jgikbase.test.idmapping.test_utils import assert_exception_correct

LONG_STR = 'a' * 100


def test_authsource_init_pass():
    as_ = AuthsourceID('abcdefghijklmnopqrst')
    assert as_.authsource == 'abcdefghijklmnopqrst'

    as_ = AuthsourceID('uvwxyz')
    assert as_.authsource == 'uvwxyz'


def test_authsource_init_fail():
    fail_authsource_init(None, ValueError('authsource cannot be None'))
    fail_authsource_init('   \t    \n   ',
                         ValueError('authsource cannot be whitespace only'))
    fail_authsource_init('abcdefghijklmnopqrstu', ValueError(
        'authsource abcdefghijklmnopqrstu exceeds maximum length of 20'))
    fail_authsource_init('fooo1b&',
                         ValueError('Illegal character in authsource fooo1b&: 1'))


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


def test_user_init_pass():
    u = User(AuthsourceID('foo'), LONG_STR[0:64] + 'abcdefghijklmnopqrstuvwxyz0123456789')
    # yuck, but don't want to add a hash fn to authsource unless necessary
    assert u.authsource.authsource == 'foo'
    assert u.username == LONG_STR[0:64] + 'abcdefghijklmnopqrstuvwxyz0123456789'


def test_user_init_fail():
    as_ = AuthsourceID('bar')
    fail_user_init(None, 'foo', ValueError('authsource cannot be None'))
    fail_user_init(as_, None, ValueError('username cannot be None'))
    fail_user_init(as_, '       \t      \n   ',
                   ValueError('username cannot be whitespace only'))
    fail_user_init(as_, LONG_STR + 'b',
                   ValueError('username ' + LONG_STR + 'b exceeds maximum length of 100'))
    for c in '0123456789':
        fail_user_init(as_, c + 'foo',
                       ValueError('username ' + c + 'foo must start with a letter'))
    for c in '*&@-+\n\t~_':
        fail_user_init(as_, 'foo1d' + c,
                       ValueError('Illegal character in username foo1d' + c + ': ' + c))


def fail_user_init(authsource: AuthsourceID, username: str, expected: Exception):
    try:
        User(authsource, username)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)
