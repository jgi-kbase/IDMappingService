from jgikbase.idmapping.core.user import Authsource, User
from pytest import fail
from jgikbase.test.idmapping.test_utils import assert_exception_correct


def test_authsource_init_pass():
    as_ = Authsource('foo')
    assert as_.authsource == 'foo'


def test_authsource_init_fail():
    fail_authsource_init(None, ValueError('authsource cannot be None'))
    fail_authsource_init('   \t    \n   ',
                         ValueError('authsource cannot be None or whitespace only'))


def fail_authsource_init(source: str, expected: Exception):
    try:
        Authsource(source)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)


def test_user_init_pass():
    u = User(Authsource('foo'), 'bar')
    # yuck, but don't want to add a hash fn to authsource unless necessary
    assert u.authsource.authsource == 'foo'
    assert u.username == 'bar'


def test_user_init_fail():
    as_ = Authsource('bar')
    fail_user_init(None, 'foo', ValueError('authsource cannot be None'))
    fail_user_init(as_, None, ValueError('username cannot be None'))
    fail_user_init(as_, '       \t      \n   ',
                   ValueError('username cannot be None or whitespace only'))


def fail_user_init(authsource: Authsource, username: str, expected: Exception):
    try:
        User(authsource, username)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)
