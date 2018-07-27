from unittest.mock import create_autospec
from jgikbase.idmapping.storage.id_mapping_storage import IDMappingStorage
from jgikbase.idmapping.core.user_handler import LocalUserHandler
from jgikbase.idmapping.core.user import AuthsourceID, User, Username
from jgikbase.idmapping.core.tokens import Token, HashedToken
from jgikbase.test.idmapping.test_utils import assert_exception_correct
from pytest import raises
from jgikbase.test.idmapping.core.tokens_test import is_base64


def test_init_fail():
    with raises(Exception) as got:
        LocalUserHandler(None)
    assert_exception_correct(got.value, TypeError('storage cannot be None'))


def test_get_authsource():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    assert LocalUserHandler(storage).get_authsource_id() == AuthsourceID('local')


def test_get_user():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    storage.get_user.return_value = Username('bar')

    assert LocalUserHandler(storage).get_user(Token('foo')) == \
        User(AuthsourceID('local'), Username('bar'))

    thash = '2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae'
    assert storage.get_user.call_args_list == [((HashedToken(thash),), {})]


def test_get_user_fail():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    with raises(Exception) as got:
        LocalUserHandler(storage).get_user(None)
    assert_exception_correct(got.value, TypeError('token cannot be None'))


def test_is_valid_user():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    storage.user_exists.return_value = True

    luh = LocalUserHandler(storage)

    assert luh.is_valid_user(Username('foo')) is True

    storage.user_exists.return_value = False

    assert luh.is_valid_user(Username('bar')) is False

    assert storage.user_exists.call_args_list == [
        ((Username('foo'),), {}),
        ((Username('bar'),), {})]


def test_is_valid_user_fail():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    with raises(Exception) as got:
        LocalUserHandler(storage).is_valid_user(None)
    assert_exception_correct(got.value, TypeError('username cannot be None'))


def test_create_user():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)

    t = LocalUserHandler(storage).create_user(Username('foo'))

    assert is_base64(t.token) is True
    assert len(t.token) is 28

    assert storage.create_local_user.call_args_list == \
        [((Username('foo'), t.get_hashed_token()), {})]


def test_create_user_fail():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    with raises(Exception) as got:
        LocalUserHandler(storage).create_user(None)
    assert_exception_correct(got.value, TypeError('username cannot be None'))


def test_new_token():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)

    t = LocalUserHandler(storage).new_token(Username('bar'))

    assert is_base64(t.token) is True
    assert len(t.token) is 28

    assert storage.update_local_user.call_args_list == \
        [((Username('bar'), t.get_hashed_token()), {})]


def test_new_token_fail():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    with raises(Exception) as got:
        LocalUserHandler(storage).new_token(None)
    assert_exception_correct(got.value, TypeError('username cannot be None'))


def test_get_users():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    storage.get_users.return_value = {Username('foo'), Username('bar')}

    assert LocalUserHandler(storage).get_users() == {Username('foo'), Username('bar')}

    assert storage.get_users.call_args_list == [((), {})]
