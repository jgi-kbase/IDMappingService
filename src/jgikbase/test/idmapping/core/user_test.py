from jgikbase.idmapping.core.user import AuthsourceID, User
from pytest import fail
from jgikbase.test.idmapping.test_utils import assert_exception_correct


def test_authsource_init_pass():
    as_ = AuthsourceID('foo')
    assert as_.authsource == 'foo'


def test_authsource_init_fail():
    fail_authsource_init(None, ValueError('authsource cannot be None'))
    fail_authsource_init('   \t    \n   ',
                         ValueError('authsource cannot be None or whitespace only'))


def fail_authsource_init(source: str, expected: Exception):
    try:
        AuthsourceID(source)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)


def test_user_init_pass():
    u = User(AuthsourceID('foo'), 'bar')
    # yuck, but don't want to add a hash fn to authsource unless necessary
    assert u.authsource.authsource == 'foo'
    assert u.username == 'bar'


def test_user_init_fail():
    as_ = AuthsourceID('bar')
    fail_user_init(None, 'foo', ValueError('authsource cannot be None'))
    fail_user_init(as_, None, ValueError('username cannot be None'))
    fail_user_init(as_, '       \t      \n   ',
                   ValueError('username cannot be None or whitespace only'))


def fail_user_init(authsource: AuthsourceID, username: str, expected: Exception):
    try:
        User(authsource, username)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)
