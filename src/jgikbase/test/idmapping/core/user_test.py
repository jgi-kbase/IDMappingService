from jgikbase.idmapping.core.user import AuthsourceID, User, LOCAL, Username
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


def test_authsource_hash():
    # string hashes will change from instance to instance of the python interpreter, and therefore
    # tests can't be written that directly test the hash value. See
    # https://docs.python.org/3/reference/datamodel.html#object.__hash__
    assert hash(AuthsourceID('foo')) == hash(AuthsourceID('foo'))
    assert hash(AuthsourceID('bar')) == hash(AuthsourceID('bar'))
    assert hash(AuthsourceID('foo')) != hash(AuthsourceID('bar'))


def test_username_init_pass():
    u = Username(LONG_STR[0:64] + 'abcdefghijklmnopqrstuvwxyz0123456789')
    assert u.name == LONG_STR[0:64] + 'abcdefghijklmnopqrstuvwxyz0123456789'


def test_username_init_fail():
    fail_username_init(None, MissingParameterError('username'))
    fail_username_init('       \t      \n   ', MissingParameterError('username'))
    fail_username_init(LONG_STR + 'b', IllegalUsernameError(
        'username ' + LONG_STR + 'b exceeds maximum length of 100'))
    for c in '0123456789':
        fail_username_init(c + 'foo',
                           IllegalUsernameError('username ' + c + 'foo must start with a letter'))
    for c in '*&@-+\n\t~_':
        fail_username_init(
            'foo1d' + c,
            IllegalUsernameError('Illegal character in username foo1d' + c + ': ' + c))


def fail_username_init(username, expected):
    try:
        Username(username)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)


def test_username_equals():
    assert Username('foo') == Username('foo')
    assert Username('foo') != Username('bar')
    assert Username('foo') != 'foo'


def test_username_hash():
    # string hashes will change from instance to instance of the python interpreter, and therefore
    # tests can't be written that directly test the hash value. See
    # https://docs.python.org/3/reference/datamodel.html#object.__hash__
    assert hash(Username('foo')) == hash(Username('foo'))
    assert hash(Username('bar')) == hash(Username('bar'))
    assert hash(Username('foo')) != hash(Username('bar'))


def test_user_init_pass():
    u = User(AuthsourceID('foo'), Username('bar'))
    assert u.authsource_id == AuthsourceID('foo')
    assert u.username == Username('bar')


def test_user_init_fail():
    fail_user_init(None, Username('foo'), TypeError('authsource_id cannot be None'))
    fail_user_init(AuthsourceID('bar'), None, TypeError('username cannot be None'))


def fail_user_init(authsource: AuthsourceID, username: Username, expected: Exception):
    try:
        User(authsource, username)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)


def test_user_equals():
    assert User(AuthsourceID('foo'), Username('baz')) == User(AuthsourceID('foo'), Username('baz'))
    assert User(AuthsourceID('foo'), Username('baz')) != User(AuthsourceID('bar'), Username('baz'))
    assert User(AuthsourceID('foo'), Username('baz')) != User(AuthsourceID('foo'), Username('bar'))
    assert User(AuthsourceID('foo'), Username('baz')) != AuthsourceID('foo')


def test_user_hash():
    # string hashes will change from instance to instance of the python interpreter, and therefore
    # tests can't be written that directly test the hash value. See
    # https://docs.python.org/3/reference/datamodel.html#object.__hash__
    assert hash(User(AuthsourceID('foo'), Username('bar'))) == hash(
        User(AuthsourceID('foo'), Username('bar')))
    assert hash(User(AuthsourceID('bar'), Username('foo'))) == hash(
        User(AuthsourceID('bar'), Username('foo')))
    assert hash(User(AuthsourceID('baz'), Username('foo'))) != hash(
        User(AuthsourceID('bar'), Username('foo')))
    assert hash(User(AuthsourceID('bar'), Username('fob'))) != hash(
        User(AuthsourceID('bar'), Username('foo')))
