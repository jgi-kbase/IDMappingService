from jgikbase.idmapping.core.user import Authsource, User
from pytest import fail
from jgikbase.test.idmapping.test_utils import assert_exception_correct

LONG_STR = 'a' * 100


def test_authsource_init_pass():
    as_ = Authsource('abcdefghijklmnopqrst')
    assert as_.authsource == 'abcdefghijklmnopqrst'

    as_ = Authsource('uvwxyz')
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
        Authsource(source)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)


def test_user_init_pass():
    u = User(Authsource('foo'), LONG_STR[0:63] + 'abcdefghijklmnopqrstuvwxyz0123456789_')
    # yuck, but don't want to add a hash fn to authsource unless necessary
    assert u.authsource.authsource == 'foo'
    assert u.username == LONG_STR[0:63] + 'abcdefghijklmnopqrstuvwxyz0123456789_'


def test_user_init_fail():
    as_ = Authsource('bar')
    fail_user_init(None, 'foo', ValueError('authsource cannot be None'))
    fail_user_init(as_, None, ValueError('username cannot be None'))
    fail_user_init(as_, '       \t      \n   ',
                   ValueError('username cannot be whitespace only'))
    fail_user_init(as_, LONG_STR + 'b',
                   ValueError('username ' + LONG_STR + 'b exceeds maximum length of 100'))
    for c in '0123456789_':
        fail_user_init(as_, c + 'foo',
                       ValueError('username ' + c + 'foo must start with a letter'))
    for c in '*&@-+\n\t~':
        fail_user_init(as_, 'foo1_d' + c,
                       ValueError('Illegal character in username foo1_d' + c + ': ' + c))


def fail_user_init(authsource: Authsource, username: str, expected: Exception):
    try:
        User(authsource, username)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)
