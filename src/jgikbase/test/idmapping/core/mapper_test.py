from unittest.mock import create_autospec
from jgikbase.idmapping.storage.id_mapping_storage import IDMappingStorage
from jgikbase.idmapping.core.mapper import IDMapper
from jgikbase.idmapping.core.object_id import NamespaceID, Namespace
from pytest import raises
from jgikbase.test.idmapping.test_utils import assert_exception_correct
from jgikbase.idmapping.core.user_handler import UserHandlerSet
from jgikbase.idmapping.core.user import AuthsourceID, Username, User
from jgikbase.idmapping.core.errors import NoSuchUserError, UnauthorizedError
from jgikbase.idmapping.core.tokens import Token


def test_init_fail():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserHandlerSet, spec_set=True, instance=True)

    a = AuthsourceID('a')

    fail_init(None, set(), storage, TypeError('user_handlers cannot be None'))
    fail_init(handlers, None, storage, TypeError('admin_authsources cannot be None'))
    fail_init(handlers, set([a, None]), storage, TypeError('None item in admin_authsources'))
    fail_init(handlers, set(), None, TypeError('storage cannot be None'))


def fail_init(handlers, admin_authsources, storage, expected):
    with raises(Exception) as got:
        IDMapper(handlers, admin_authsources, storage)
    assert_exception_correct(got.value, expected)


def test_create_namespace():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserHandlerSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('as')]), storage)

    handlers.get_user.return_value = (User(AuthsourceID('as'), Username('foo')), True)

    idm.create_namespace(AuthsourceID('as'), Token('bar'), NamespaceID('foo'))

    assert handlers.get_user.call_args_list == [((AuthsourceID('as'), Token('bar'),), {})]
    assert storage.create_namespace.call_args_list == [((NamespaceID('foo'),), {})]


def test_create_namespace_fail_None_input():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserHandlerSet, spec_set=True, instance=True)
    idm = IDMapper(handlers, set(), storage)

    as_ = AuthsourceID('foo')
    t = Token('t')
    n = NamespaceID('n')

    # authsource id is checked by the handler set
    fail_create_namespace(idm, as_, None, n, TypeError('token cannot be None'))
    fail_create_namespace(idm, as_, t, None, TypeError('namespace_id cannot be None'))


def test_create_namespace_fail_no_admin_authsource_provider():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserHandlerSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('bs')]), storage)

    fail_create_namespace(idm, AuthsourceID('as'), Token('t'), NamespaceID('n'), UnauthorizedError(
        'Auth source as is not configured as a provider of system administration status'))


def test_create_namespace_fail_not_admin():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserHandlerSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('as')]), storage)

    handlers.get_user.return_value = (User(AuthsourceID('as'), Username('foo')), False)

    fail_create_namespace(idm, AuthsourceID('as'), Token('t'), NamespaceID('n'),
                          UnauthorizedError('User as/foo is not a system administrator'))


def fail_create_namespace(idm, authsource, token, namespace_id, expected):
    with raises(Exception) as got:
        idm.create_namespace(authsource, token, namespace_id)
    assert_exception_correct(got.value, expected)


def test_add_user_to_namespace():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserHandlerSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('astwo')]), storage)

    handlers.get_user.return_value = (User(AuthsourceID('astwo'), Username('foo')), True)
    handlers.is_valid_user.return_value = True

    idm.add_user_to_namespace(
        AuthsourceID('astwo'),
        Token('t'),
        NamespaceID('ns1'),
        User(AuthsourceID('asone'), Username('u1')))

    assert handlers.get_user.call_args_list == [((AuthsourceID('astwo'), Token('t'),), {})]
    assert handlers.is_valid_user.call_args_list == \
        [((User(AuthsourceID('asone'), Username('u1')),), {})]
    assert storage.add_user_to_namespace.call_args_list == \
        [((NamespaceID('ns1'), User(AuthsourceID('asone'), Username('u1'))), {})]


def test_add_user_to_namespace_fail_None_input():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserHandlerSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    as_ = AuthsourceID('a')
    t = Token('t')
    n = NamespaceID('n')
    u = User(AuthsourceID('b'), Username('u'))

    # authsource id is checked by the handler set
    fail_add_user_to_namespace(idm, as_, None, n, u, TypeError('token cannot be None'))
    fail_add_user_to_namespace(idm, as_, t, None, u, TypeError('namespace_id cannot be None'))
    fail_add_user_to_namespace(idm, as_, t, n, None, TypeError('user cannot be None'))


def test_add_user_to_namespace_fail_no_admin_authsource_provider():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserHandlerSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('bs')]), storage)

    fail_add_user_to_namespace(idm, AuthsourceID('as'), Token('t'), NamespaceID('n'),
                               User(AuthsourceID('as'), Username('u')),
                               UnauthorizedError(
        'Auth source as is not configured as a provider of system administration status'))


def test_add_user_to_namespace_fail_not_admin():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserHandlerSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('as')]), storage)

    handlers.get_user.return_value = (User(AuthsourceID('as'), Username('foo')), False)

    fail_add_user_to_namespace(idm, AuthsourceID('as'), Token('t'), NamespaceID('n'),
                               User(AuthsourceID('as'), Username('u')),
                               UnauthorizedError('User as/foo is not a system administrator'))


def test_add_user_to_namespace_fail_no_such_user():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserHandlerSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('asone')]), storage)

    handlers.get_user.return_value = (User(AuthsourceID('asone'), Username('bar')), True)
    handlers.is_valid_user.return_value = False

    fail_add_user_to_namespace(idm, AuthsourceID('asone'), Token('t'), NamespaceID('n'),
                               User(AuthsourceID('asone'), Username('u')),
                               NoSuchUserError('asone/u'))


def fail_add_user_to_namespace(idmapper, authsource, token, namespace_id, user, expected):
    with raises(Exception) as got:
        idmapper.add_user_to_namespace(authsource, token, namespace_id, user)
    assert_exception_correct(got.value, expected)


def test_remove_user_from_namespace():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserHandlerSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('astwo')]), storage)

    handlers.get_user.return_value = (User(AuthsourceID('astwo'), Username('foo')), True)
    handlers.is_valid_user.return_value = True

    idm.remove_user_from_namespace(
        AuthsourceID('astwo'),
        Token('t'),
        NamespaceID('ns1'),
        User(AuthsourceID('asone'), Username('u1')))

    assert handlers.get_user.call_args_list == [((AuthsourceID('astwo'), Token('t'),), {})]
    assert handlers.is_valid_user.call_args_list == \
        [((User(AuthsourceID('asone'), Username('u1')),), {})]
    assert storage.remove_user_from_namespace.call_args_list == \
        [((NamespaceID('ns1'), User(AuthsourceID('asone'), Username('u1'))), {})]


def test_remove_user_from_namespace_fail_None_input():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserHandlerSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    as_ = AuthsourceID('a')
    t = Token('t')
    n = NamespaceID('n')
    u = User(AuthsourceID('b'), Username('u'))

    # authsource id is checked by the handler set
    fail_remove_user_from_namespace(idm, as_, None, n, u, TypeError('token cannot be None'))
    fail_remove_user_from_namespace(idm, as_, t, None, u, TypeError('namespace_id cannot be None'))
    fail_remove_user_from_namespace(idm, as_, t, n, None, TypeError('user cannot be None'))


def test_remove_user_from_namespace_fail_no_admin_authsource_provider():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserHandlerSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('bs')]), storage)

    fail_remove_user_from_namespace(idm, AuthsourceID('as'), Token('t'), NamespaceID('n'),
                                    User(AuthsourceID('as'), Username('u')),
                                    UnauthorizedError(
        'Auth source as is not configured as a provider of system administration status'))


def test_remove_user_from_namespace_fail_not_admin():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserHandlerSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('as')]), storage)

    handlers.get_user.return_value = (User(AuthsourceID('as'), Username('foo')), False)

    fail_remove_user_from_namespace(idm, AuthsourceID('as'), Token('t'), NamespaceID('n'),
                                    User(AuthsourceID('as'), Username('u')),
                                    UnauthorizedError('User as/foo is not a system administrator'))


def test_remove_user_from_namespace_fail_no_such_user():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserHandlerSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('asone')]), storage)

    handlers.get_user.return_value = (User(AuthsourceID('asone'), Username('bar')), True)
    handlers.is_valid_user.return_value = False

    fail_remove_user_from_namespace(
        idm, AuthsourceID('asone'), Token('t'), NamespaceID('n'),
        User(AuthsourceID('asone'), Username('u')),
        NoSuchUserError('asone/u'))


def fail_remove_user_from_namespace(idmapper, authsource, token, namespace_id, user, expected):
    with raises(Exception) as got:
        idmapper.remove_user_from_namespace(authsource, token, namespace_id, user)
    assert_exception_correct(got.value, expected)


def test_set_namespace_publicly_mappable():
    check_set_namespace_publicly_mappable(True)
    check_set_namespace_publicly_mappable(False)


def check_set_namespace_publicly_mappable(pub_value):
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserHandlerSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('asone')]), storage)

    handlers.get_user.return_value = (User(AuthsourceID('asone'), Username('u')), False)
    storage.get_namespace.return_value = Namespace(NamespaceID('n'), False, set([
        User(AuthsourceID('astwo'), Username('u2')),
        User(AuthsourceID('asone'), Username('u')),
        User(AuthsourceID('asthree'), Username('u'))]))

    idm.set_namespace_publicly_mappable(
        AuthsourceID('asone'),
        Token('t'),
        NamespaceID('n'),
        pub_value)

    assert handlers.get_user.call_args_list == [((AuthsourceID('asone'), Token('t'),), {})]
    assert storage.get_namespace.call_args_list == [((NamespaceID('n'),), {})]
    assert storage.set_namespace_publicly_mappable.call_args_list == \
        [((NamespaceID('n'), pub_value), {})]


def test_set_namespace_publicly_mappable_fail_None_input():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserHandlerSet, spec_set=True, instance=True)
    idm = IDMapper(handlers, set(), storage)

    aid = AuthsourceID('asone')
    t = Token('t')
    n = NamespaceID('id')
    e = ' cannot be None'

    # handler set checks the authsource id
    fail_set_namespace_publicly_mappable(idm, aid, None, n, TypeError('token' + e))
    fail_set_namespace_publicly_mappable(idm, aid, t, None, TypeError('namespace_id' + e))


def test_set_namespace_publicly_mappable_fail_unauthed():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserHandlerSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('asone')]), storage)

    handlers.get_user.return_value = (User(AuthsourceID('asone'), Username('u')), False)
    storage.get_namespace.return_value = Namespace(NamespaceID('n'), False, set([
        User(AuthsourceID('asone'), Username('u2')),
        User(AuthsourceID('asthree'), Username('u'))]))

    fail_set_namespace_publicly_mappable(
        idm, AuthsourceID('asone'), Token('t'), NamespaceID('n'),
        UnauthorizedError('User asone/u may not administrate namespace n'))


def fail_set_namespace_publicly_mappable(idmapper, auth_id, token, namespace_id, expected):
    with raises(Exception) as got:
        idmapper.set_namespace_publicly_mappable(auth_id, token, namespace_id, False)
    assert_exception_correct(got.value, expected)
