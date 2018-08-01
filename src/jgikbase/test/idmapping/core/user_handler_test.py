from unittest.mock import create_autospec
from jgikbase.idmapping.storage.id_mapping_storage import IDMappingStorage
from jgikbase.idmapping.core.user_handler import LocalUserHandler, UserHandlerSet, UserHandler
from jgikbase.idmapping.core.user import AuthsourceID, User, Username
from jgikbase.idmapping.core.tokens import Token, HashedToken
from jgikbase.test.idmapping.test_utils import assert_exception_correct
from pytest import raises
from jgikbase.test.idmapping.core.tokens_test import is_base64
import time


def test_set_init_fail():
    handler = create_autospec(UserHandler, spec_set=True, instance=True)

    fail_set_init(None, TypeError('user_handlers cannot be None'))
    fail_set_init(set([handler, None]), TypeError('None item in user_handlers'))


def fail_set_init(handlers, expected):
    with raises(Exception) as got:
        UserHandlerSet(handlers)
    assert_exception_correct(got.value, expected)


def test_set_get_user_default_cache_ttl():
    handler = create_autospec(UserHandler, spec_set=True, instance=True)
    timer = create_autospec(time.time, spec_set=True)
    handler.get_authsource_id.return_value = AuthsourceID('as')

    hset = UserHandlerSet(set([handler]), timer)

    check_set_get_user_default_cache_ttl(hset, handler, timer, [0, 299, 300, 301])


def test_set_get_user_default_cache_ttl_set_ttl():
    check_set_get_user_default_cache_ttl_set_ttl(100, [0, 99, 100, 101])
    check_set_get_user_default_cache_ttl_set_ttl(500, [0, 499, 500, 501])


def check_set_get_user_default_cache_ttl_set_ttl(ttl, timervals):
    handler = create_autospec(UserHandler, spec_set=True, instance=True)
    timer = create_autospec(time.time, spec_set=True)
    handler.get_authsource_id.return_value = AuthsourceID('as')

    hset = UserHandlerSet(set([handler]), timer, cache_user_expiration=ttl)

    check_set_get_user_default_cache_ttl(hset, handler, timer, timervals)


def check_set_get_user_default_cache_ttl(hset, handler, timer, timervals):

    handler.get_user.return_value = (User(AuthsourceID('as'), Username('u')), False, None, None)
    timer.return_value = timervals[0]

    # user will not be in cache
    assert hset.get_user(AuthsourceID('as'), Token('t')) == \
        (User(AuthsourceID('as'), Username('u')), False)

    # user is now cached
    handler.get_user.return_value = None  # should cause error if called from now on
    timer.return_value = timervals[1]  # just below default cache time

    assert hset.get_user(AuthsourceID('as'), Token('t')) == \
        (User(AuthsourceID('as'), Username('u')), False)

    # now expire the user
    handler.get_user.return_value = (User(AuthsourceID('as'), Username('u')), True, None, None)
    timer.return_value = timervals[2]

    assert hset.get_user(AuthsourceID('as'), Token('t')) == \
        (User(AuthsourceID('as'), Username('u')), True)

    # get the user again, should be cached.
    handler.get_user.return_value = None  # should cause error if called from now on
    timer.return_value = timervals[3]

    assert hset.get_user(AuthsourceID('as'), Token('t')) == \
        (User(AuthsourceID('as'), Username('u')), True)

    assert handler.get_user.call_args_list == [((Token('t'),), {}), ((Token('t'),), {})]


def test_set_is_valid_user_default_cache_ttl():
    handler = create_autospec(UserHandler, spec_set=True, instance=True)
    timer = create_autospec(time.time, spec_set=True)
    handler.get_authsource_id.return_value = AuthsourceID('as')

    hset = UserHandlerSet(set([handler]), timer)

    check_set_is_valid_user_default_cache_ttl(hset, handler, timer, [0, 3599, 3600, 3601])


def test_set_is_valid_user_default_cache_ttl_set_ttl():
    check_set_is_valid_user_default_cache_ttl_set_ttl(100, [0, 99, 100, 101])
    check_set_is_valid_user_default_cache_ttl_set_ttl(10000, [0, 9999, 10000, 10001])


def check_set_is_valid_user_default_cache_ttl_set_ttl(ttl, timervals):
    handler = create_autospec(UserHandler, spec_set=True, instance=True)
    timer = create_autospec(time.time, spec_set=True)
    handler.get_authsource_id.return_value = AuthsourceID('as')

    hset = UserHandlerSet(set([handler]), timer, cache_is_valid_expiration=ttl)

    check_set_is_valid_user_default_cache_ttl(hset, handler, timer, timervals)


def check_set_is_valid_user_default_cache_ttl(hset, handler, timer, timervals):

    handler.is_valid_user.return_value = (True, None, None)
    timer.return_value = timervals[0]

    # user will not be in cache
    assert hset.is_valid_user(User(AuthsourceID('as'), Username('u'))) is True

    # user is now cached
    handler.is_valid_user.return_value = None  # should cause error if called from now on
    timer.return_value = timervals[1]  # just below default cache time

    assert hset.is_valid_user(User(AuthsourceID('as'), Username('u'))) is True

    # now expire the user
    handler.is_valid_user.return_value = (True, None, None)
    timer.return_value = timervals[2]

    assert hset.is_valid_user(User(AuthsourceID('as'), Username('u'))) is True

    # get the user again, should be cached
    handler.is_valid_user.return_value = None  # should cause error if called from now on
    timer.return_value = timervals[3]

    assert hset.is_valid_user(User(AuthsourceID('as'), Username('u'))) is True

    assert handler.is_valid_user.call_args_list == [((Username('u'),), {}), ((Username('u'),), {})]


def test_set_is_valid_user_invalid_user():
    # invalid users shouldn't get cached.
    handler = create_autospec(UserHandler, spec_set=True, instance=True)
    timer = create_autospec(time.time, spec_set=True)
    handler.get_authsource_id.return_value = AuthsourceID('as')

    hset = UserHandlerSet(set([handler]), timer)

    handler.is_valid_user.return_value = (False, None, None)
    timer.return_value = 0

    # user will not be in cache
    assert hset.is_valid_user(User(AuthsourceID('as'), Username('u'))) is False

    # would normally expect a cache time of 3600s, but should not be cached here.

    timer.return_value = 10

    assert hset.is_valid_user(User(AuthsourceID('as'), Username('u'))) is False

    assert handler.is_valid_user.call_args_list == [((Username('u'),), {}), ((Username('u'),), {})]


def test_local_init_fail():
    with raises(Exception) as got:
        LocalUserHandler(None)
    assert_exception_correct(got.value, TypeError('storage cannot be None'))


def test_local_get_authsource():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    assert LocalUserHandler(storage).get_authsource_id() == AuthsourceID('local')


def test_local_get_user_admin():
    check_local_get_user_admin(True)
    check_local_get_user_admin(False)


def check_local_get_user_admin(isadmin):
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    storage.get_user.return_value = (Username('bar'), isadmin)

    assert LocalUserHandler(storage).get_user(Token('foo')) == \
        (User(AuthsourceID('local'), Username('bar')), isadmin, None, 300)

    thash = '2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae'
    assert storage.get_user.call_args_list == [((HashedToken(thash),), {})]


def test_local_get_user_fail():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    with raises(Exception) as got:
        LocalUserHandler(storage).get_user(None)
    assert_exception_correct(got.value, TypeError('token cannot be None'))


def test_local_is_valid_user():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    storage.user_exists.return_value = True

    luh = LocalUserHandler(storage)

    assert luh.is_valid_user(Username('foo')) == (True, None, 3600)

    storage.user_exists.return_value = False

    assert luh.is_valid_user(Username('bar')) == (False, None, 3600)

    assert storage.user_exists.call_args_list == [
        ((Username('foo'),), {}),
        ((Username('bar'),), {})]


def test_local_is_valid_user_fail():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    with raises(Exception) as got:
        LocalUserHandler(storage).is_valid_user(None)
    assert_exception_correct(got.value, TypeError('username cannot be None'))


def test_local_create_user():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)

    t = LocalUserHandler(storage).create_user(Username('foo'))

    assert is_base64(t.token) is True
    assert len(t.token) is 28

    assert storage.create_local_user.call_args_list == \
        [((Username('foo'), t.get_hashed_token()), {})]


def test_local_create_user_fail():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    with raises(Exception) as got:
        LocalUserHandler(storage).create_user(None)
    assert_exception_correct(got.value, TypeError('username cannot be None'))


def test_local_new_token():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)

    t = LocalUserHandler(storage).new_token(Username('bar'))

    assert is_base64(t.token) is True
    assert len(t.token) is 28

    assert storage.update_local_user_token.call_args_list == \
        [((Username('bar'), t.get_hashed_token()), {})]


def test_local_new_token_fail():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    with raises(Exception) as got:
        LocalUserHandler(storage).new_token(None)
    assert_exception_correct(got.value, TypeError('username cannot be None'))


def test_local_get_users():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    storage.get_users.return_value = {Username('foo'): False, Username('bar'): True}

    assert LocalUserHandler(storage).get_users() == {Username('foo'): False,
                                                     Username('bar'): True}

    assert storage.get_users.call_args_list == [((), {})]
