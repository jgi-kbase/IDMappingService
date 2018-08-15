from unittest.mock import create_autospec
from jgikbase.idmapping.storage.id_mapping_storage import IDMappingStorage
from jgikbase.idmapping.core.mapper import IDMapper
from jgikbase.idmapping.core.object_id import NamespaceID, Namespace, ObjectID
from pytest import raises
from jgikbase.test.idmapping.test_utils import assert_exception_correct
from jgikbase.idmapping.core.user_lookup import UserLookupSet
from jgikbase.idmapping.core.user import AuthsourceID, Username, User
from jgikbase.idmapping.core.errors import NoSuchUserError, UnauthorizedError, NoSuchNamespaceError
from jgikbase.idmapping.core.tokens import Token
from pytest import fixture
import logging
from logging import Formatter, StreamHandler
from typing import List  # @UnusedImport pydev
from logging import LogRecord  # @UnusedImport pydev


class TerstFermerttr(Formatter):

    logs: List[LogRecord] = []

    def __init__(self):
        pass

    def format(self, record):
        self.logs.append(record)
        return 'no logs here, no sir'


@fixture(scope='module')
def init_logger():
    print('log collector init')
    handler = StreamHandler()
    formatter = TerstFermerttr()
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel('INFO')
    return formatter.logs


@fixture
def log_collector(init_logger):
    print('clearing logs')
    init_logger.clear()
    return init_logger


def assert_logs_correct(logs, logstring):
    assert len(logs) == 1
    logrecord = logs[0]
    assert logrecord.name == 'jgikbase.idmapping.core.mapper'
    assert logrecord.levelname == 'INFO'
    assert logrecord.getMessage() == logstring


def test_init_fail():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    a = AuthsourceID('a')

    fail_init(None, set(), storage, TypeError('user_lookup cannot be None'))
    fail_init(handlers, None, storage, TypeError('admin_authsources cannot be None'))
    fail_init(handlers, set([a, None]), storage, TypeError('None item in admin_authsources'))
    fail_init(handlers, set(), None, TypeError('storage cannot be None'))


def fail_init(handlers, admin_authsources, storage, expected):
    with raises(Exception) as got:
        IDMapper(handlers, admin_authsources, storage)
    assert_exception_correct(got.value, expected)


def test_create_namespace(log_collector):
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('as')]), storage)

    handlers.get_user.return_value = (User(AuthsourceID('as'), Username('foo')), True)

    idm.create_namespace(AuthsourceID('as'), Token('bar'), NamespaceID('baz'))

    assert handlers.get_user.call_args_list == [((AuthsourceID('as'), Token('bar'),), {})]
    assert storage.create_namespace.call_args_list == [((NamespaceID('baz'),), {})]

    assert_logs_correct(log_collector, 'Admin as/foo created namespace baz')


def test_create_namespace_fail_None_input():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)
    idm = IDMapper(handlers, set(), storage)

    as_ = AuthsourceID('foo')
    t = Token('t')
    n = NamespaceID('n')

    # authsource id is checked by the handler set
    fail_create_namespace(idm, as_, None, n, TypeError('token cannot be None'))
    fail_create_namespace(idm, as_, t, None, TypeError('namespace_id cannot be None'))


def test_create_namespace_fail_no_admin_authsource_provider():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('bs')]), storage)

    fail_create_namespace(idm, AuthsourceID('as'), Token('t'), NamespaceID('n'), UnauthorizedError(
        'Auth source as is not configured as a provider of system administration status'))


def test_create_namespace_fail_not_admin():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('as')]), storage)

    handlers.get_user.return_value = (User(AuthsourceID('as'), Username('foo')), False)

    fail_create_namespace(idm, AuthsourceID('as'), Token('t'), NamespaceID('n'),
                          UnauthorizedError('User as/foo is not a system administrator'))


def fail_create_namespace(idm, authsource, token, namespace_id, expected):
    with raises(Exception) as got:
        idm.create_namespace(authsource, token, namespace_id)
    assert_exception_correct(got.value, expected)


def test_add_user_to_namespace(log_collector):
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

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

    assert_logs_correct(log_collector, 'Admin astwo/foo added user asone/u1 to namespace ns1')


def test_add_user_to_namespace_fail_None_input():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

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
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('bs')]), storage)

    fail_add_user_to_namespace(idm, AuthsourceID('as'), Token('t'), NamespaceID('n'),
                               User(AuthsourceID('as'), Username('u')),
                               UnauthorizedError(
        'Auth source as is not configured as a provider of system administration status'))


def test_add_user_to_namespace_fail_not_admin():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('as')]), storage)

    handlers.get_user.return_value = (User(AuthsourceID('as'), Username('foo')), False)

    fail_add_user_to_namespace(idm, AuthsourceID('as'), Token('t'), NamespaceID('n'),
                               User(AuthsourceID('as'), Username('u')),
                               UnauthorizedError('User as/foo is not a system administrator'))


def test_add_user_to_namespace_fail_no_such_user():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

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


def test_remove_user_from_namespace(log_collector):
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('astwo')]), storage)

    handlers.get_user.return_value = (User(AuthsourceID('astwo'), Username('foo')), True)

    idm.remove_user_from_namespace(
        AuthsourceID('astwo'),
        Token('t'),
        NamespaceID('ns1'),
        User(AuthsourceID('asone'), Username('u1')))

    assert handlers.get_user.call_args_list == [((AuthsourceID('astwo'), Token('t'),), {})]
    assert storage.remove_user_from_namespace.call_args_list == \
        [((NamespaceID('ns1'), User(AuthsourceID('asone'), Username('u1'))), {})]

    assert_logs_correct(log_collector, 'Admin astwo/foo removed user asone/u1 from namespace ns1')


def test_remove_user_from_namespace_fail_None_input():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

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
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('bs')]), storage)

    fail_remove_user_from_namespace(idm, AuthsourceID('as'), Token('t'), NamespaceID('n'),
                                    User(AuthsourceID('as'), Username('u')),
                                    UnauthorizedError(
        'Auth source as is not configured as a provider of system administration status'))


def test_remove_user_from_namespace_fail_not_admin():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set([AuthsourceID('as')]), storage)

    handlers.get_user.return_value = (User(AuthsourceID('as'), Username('foo')), False)

    fail_remove_user_from_namespace(idm, AuthsourceID('as'), Token('t'), NamespaceID('n'),
                                    User(AuthsourceID('as'), Username('u')),
                                    UnauthorizedError('User as/foo is not a system administrator'))


def fail_remove_user_from_namespace(idmapper, authsource, token, namespace_id, user, expected):
    with raises(Exception) as got:
        idmapper.remove_user_from_namespace(authsource, token, namespace_id, user)
    assert_exception_correct(got.value, expected)


def test_set_namespace_publicly_mappable(log_collector):
    check_set_namespace_publicly_mappable(True, log_collector)
    log_collector.clear()
    check_set_namespace_publicly_mappable(False, log_collector)


def check_set_namespace_publicly_mappable(pub_value, log_collector):
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

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

    print(log_collector)

    assert_logs_correct(log_collector, 'User asone/u set namespace n public map property to ' +
                        str(pub_value))


def test_set_namespace_publicly_mappable_fail_None_input():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)
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
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

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


def test_get_namespace_no_auth():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    storage.get_namespace.return_value = Namespace(NamespaceID('n'), True, set([
        User(AuthsourceID('a'), Username('u')), User(AuthsourceID('a'), Username('u1'))]))

    assert idm.get_namespace(NamespaceID('n')) == Namespace(NamespaceID('n'), True)
    assert storage.get_namespace.call_args_list == [((NamespaceID('n'), ), {})]


def test_get_namespace_not_admin():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    storage.get_namespace.return_value = Namespace(NamespaceID('n'), True, set([
        User(AuthsourceID('a'), Username('u')), User(AuthsourceID('a'), Username('u1'))]))
    handlers.get_user.return_value = (User(AuthsourceID('b'), Username('u2')), False)

    assert idm.get_namespace(NamespaceID('n'), AuthsourceID('b'), Token('t')) == Namespace(
        NamespaceID('n'), True, None)
    assert storage.get_namespace.call_args_list == [((NamespaceID('n'), ), {})]
    assert handlers.get_user.call_args_list == [((AuthsourceID('b'), Token('t')), {})]


def test_get_namespace_sysadmin():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    storage.get_namespace.return_value = Namespace(NamespaceID('n'), True, set([
        User(AuthsourceID('a'), Username('u')), User(AuthsourceID('a'), Username('u1'))]))
    handlers.get_user.return_value = (User(AuthsourceID('b'), Username('u2')), True)

    assert idm.get_namespace(NamespaceID('n'), AuthsourceID('b'), Token('t')) == Namespace(
        NamespaceID('n'), True, set([
            User(AuthsourceID('a'), Username('u')), User(AuthsourceID('a'), Username('u1'))]))
    assert storage.get_namespace.call_args_list == [((NamespaceID('n'), ), {})]
    assert handlers.get_user.call_args_list == [((AuthsourceID('b'), Token('t')), {})]


def test_get_namespace_ns_admin():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    storage.get_namespace.return_value = Namespace(NamespaceID('n'), True, set([
        User(AuthsourceID('a'), Username('u')), User(AuthsourceID('b'), Username('u1'))]))
    handlers.get_user.return_value = (User(AuthsourceID('b'), Username('u1')), False)

    assert idm.get_namespace(NamespaceID('n'), AuthsourceID('b'), Token('t')) == Namespace(
        NamespaceID('n'), True, set([
            User(AuthsourceID('a'), Username('u')), User(AuthsourceID('b'), Username('u1'))]))
    assert storage.get_namespace.call_args_list == [((NamespaceID('n'), ), {})]
    assert handlers.get_user.call_args_list == [((AuthsourceID('b'), Token('t')), {})]


def test_get_namespace_fail_None_input():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    n = NamespaceID('n')
    a = AuthsourceID('a')
    t = Token('t')

    e = 'If token or authsource_id is specified, both must be specified'
    fail_get_namespace(idm, None, a, t, TypeError('namespace_id cannot be None'))
    fail_get_namespace(idm, n, None, t, TypeError(e))
    fail_get_namespace(idm, n, a, None, TypeError(e))


def fail_get_namespace(idm, namespace_id, authsource_id, token, expected):
    with raises(Exception) as got:
        idm.get_namespace(namespace_id, authsource_id, token)
    assert_exception_correct(got.value, expected)


def test_get_namespaces_empty():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    storage.get_namespaces.return_value = set()

    assert idm.get_namespaces() == (set(), set())
    assert storage.get_namespaces.call_args_list == [((), {})]


def test_get_namespaces_only_public():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    storage.get_namespaces.return_value = set([Namespace(NamespaceID('n1'), True),
                                               Namespace(NamespaceID('n2'), True)])

    assert idm.get_namespaces() == (set([NamespaceID('n1'), NamespaceID('n2')]), set())
    assert storage.get_namespaces.call_args_list == [((), {})]


def test_get_namespaces_only_private():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    storage.get_namespaces.return_value = set([Namespace(NamespaceID('n3'), False),
                                               Namespace(NamespaceID('n4'), False)])

    assert idm.get_namespaces() == (set(), set([NamespaceID('n3'), NamespaceID('n4')]))
    assert storage.get_namespaces.call_args_list == [((), {})]


def test_get_namespaces_both():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    storage.get_namespaces.return_value = set([Namespace(NamespaceID('n1'), True),
                                               Namespace(NamespaceID('n2'), True),
                                               Namespace(NamespaceID('n3'), False),
                                               Namespace(NamespaceID('n4'), False)])

    assert idm.get_namespaces() == (set([NamespaceID('n1'), NamespaceID('n2')]),
                                    set([NamespaceID('n3'), NamespaceID('n4')]))
    assert storage.get_namespaces.call_args_list == [((), {})]


def test_create_mapping_publicly_mappable(log_collector):
    check_create_mapping(Namespace(NamespaceID('n2'), True), log_collector)


def test_create_mapping_privately_mappable(log_collector):
    targetns = Namespace(NamespaceID('n2'), False, set([
            User(AuthsourceID('a'), Username('n')), User(AuthsourceID('b'), Username('n2'))]))
    check_create_mapping(targetns, log_collector)


def check_create_mapping(targetns: Namespace, log_collector):
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    handlers.get_user.return_value = (User(AuthsourceID('a'), Username('n')), False)
    storage.get_namespace.side_effect = [
        Namespace(NamespaceID('n1'), False, set([
            User(AuthsourceID('a'), Username('n')), User(AuthsourceID('a'), Username('n2'))])),
        targetns]

    idm.create_mapping(AuthsourceID('a'), Token('t'),
                       ObjectID(NamespaceID('n1'), 'o1'),
                       ObjectID(NamespaceID('n2'), 'o2'))

    assert handlers.get_user.call_args_list == [((AuthsourceID('a'), Token('t'),), {})]
    assert storage.get_namespace.call_args_list == [((NamespaceID('n1'),), {}),
                                                    ((NamespaceID('n2'),), {})]
    assert storage.add_mapping.call_args_list == [((ObjectID(NamespaceID('n1'), 'o1'),
                                                    ObjectID(NamespaceID('n2'), 'o2')), {})]

    assert_logs_correct(log_collector, 'User a/n created mapping n1/o1 <---> n2/o2')


def test_create_mapping_fail_None_input():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    a = AuthsourceID('a')
    t = Token('t')
    o1 = ObjectID(NamespaceID('n2'), 'o1')
    o2 = ObjectID(NamespaceID('n2'), 'o2')

    # authsource id is checked by the handler set
    fail_create_mapping(idm, a, None, o1, o2, TypeError('token cannot be None'))
    fail_create_mapping(idm, a, t, None, o2, TypeError('administrative_oid cannot be None'))
    fail_create_mapping(idm, a, t, o1, None, TypeError('oid cannot be None'))


def test_create_mapping_fail_unauthed_for_admin_namespace():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    handlers.get_user.return_value = (User(AuthsourceID('a'), Username('n')), False)
    storage.get_namespace.return_value = Namespace(NamespaceID('n1'), True, set([
            User(AuthsourceID('a'), Username('n1')), User(AuthsourceID('a'), Username('n2'))]))

    fail_create_mapping(idm, AuthsourceID('a'), Token('t'),
                        ObjectID(NamespaceID('n1'), 'o1'),
                        ObjectID(NamespaceID('n2'), 'o2'),
                        UnauthorizedError('User a/n may not administrate namespace n1'))


def test_create_mapping_fail_unauthed_for_other_namespace():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    handlers.get_user.return_value = (User(AuthsourceID('a'), Username('n')), False)
    storage.get_namespace.side_effect = [
        Namespace(NamespaceID('n1'), True, set([
            User(AuthsourceID('a'), Username('n')), User(AuthsourceID('a'), Username('n2'))])),
        Namespace(NamespaceID('n2'), False, set([
            User(AuthsourceID('a'), Username('n2')), User(AuthsourceID('b'), Username('n2'))]))]

    fail_create_mapping(idm, AuthsourceID('a'), Token('t'),
                        ObjectID(NamespaceID('n1'), 'o1'),
                        ObjectID(NamespaceID('n2'), 'o2'),
                        UnauthorizedError('User a/n may not administrate namespace n2'))


def fail_create_mapping(idm, authsource_id, token, oid1, oid2, expected):
    with raises(Exception) as got:
        idm.create_mapping(authsource_id, token, oid1, oid2)
    assert_exception_correct(got.value, expected)


def test_remove_mapping(log_collector):
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    handlers.get_user.return_value = (User(AuthsourceID('a'), Username('n')), False)
    storage.get_namespace.side_effect = [
        Namespace(NamespaceID('n1'), False, set([
            User(AuthsourceID('a'), Username('n')), User(AuthsourceID('a'), Username('n2'))])),
        Namespace(NamespaceID('n2'), False)]

    idm.remove_mapping(AuthsourceID('a'), Token('t'),
                       ObjectID(NamespaceID('n1'), 'o1'),
                       ObjectID(NamespaceID('n2'), 'o2'))

    assert handlers.get_user.call_args_list == [((AuthsourceID('a'), Token('t'),), {})]
    assert storage.get_namespace.call_args_list == [((NamespaceID('n1'),), {}),
                                                    ((NamespaceID('n2'),), {})]
    assert storage.remove_mapping.call_args_list == [((ObjectID(NamespaceID('n1'), 'o1'),
                                                       ObjectID(NamespaceID('n2'), 'o2')), {})]

    assert_logs_correct(log_collector, 'User a/n removed mapping n1/o1 <---> n2/o2')


def test_remove_mapping_fail_None_input():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    a = AuthsourceID('a')
    t = Token('t')
    o1 = ObjectID(NamespaceID('n2'), 'o1')
    o2 = ObjectID(NamespaceID('n2'), 'o2')

    # authsource id is checked by the handler set
    fail_remove_mapping(idm, a, None, o1, o2, TypeError('token cannot be None'))
    fail_remove_mapping(idm, a, t, None, o2, TypeError('administrative_oid cannot be None'))
    fail_remove_mapping(idm, a, t, o1, None, TypeError('oid cannot be None'))


def test_remove_mapping_fail_unauthed_for_admin_namespace():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    handlers.get_user.return_value = (User(AuthsourceID('a'), Username('n')), False)
    storage.get_namespace.return_value = Namespace(NamespaceID('n1'), True, set([
            User(AuthsourceID('a'), Username('n1')), User(AuthsourceID('a'), Username('n2'))]))

    fail_remove_mapping(idm, AuthsourceID('a'), Token('t'),
                        ObjectID(NamespaceID('n1'), 'o1'),
                        ObjectID(NamespaceID('n2'), 'o2'),
                        UnauthorizedError('User a/n may not administrate namespace n1'))


def test_remove_mapping_fail_no_such_other_namespace():
    # since the return value of the 2nd get namespace call isn't used, and the reason for the
    # call is to check the namespace exists, we explicitly test the call is made by throwing
    # an exception.
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    handlers.get_user.return_value = (User(AuthsourceID('a'), Username('n')), False)
    storage.get_namespace.side_effect = [
        Namespace(NamespaceID('n1'), False, set([
            User(AuthsourceID('a'), Username('n')), User(AuthsourceID('a'), Username('n2'))])),
        NoSuchNamespaceError('n2')]

    fail_remove_mapping(idm, AuthsourceID('a'), Token('t'),
                        ObjectID(NamespaceID('n1'), 'o1'),
                        ObjectID(NamespaceID('n2'), 'o2'),
                        NoSuchNamespaceError('n2'))


def fail_remove_mapping(idm, authsource_id, token, oid1, oid2, expected):
    with raises(Exception) as got:
        idm.remove_mapping(authsource_id, token, oid1, oid2)
    assert_exception_correct(got.value, expected)


def test_get_mappings():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    storage.get_namespaces.return_value = set([Namespace(NamespaceID('n'), False)])
    storage.find_mappings.return_value = (
        set([ObjectID(NamespaceID('n1'), 'o1'), ObjectID(NamespaceID('n2'), 'o2')]),
        set([ObjectID(NamespaceID('n3'), 'o3'), ObjectID(NamespaceID('n4'), 'o4')]))

    assert idm.get_mappings(ObjectID(NamespaceID('n'), 'o')) == (
        set([ObjectID(NamespaceID('n1'), 'o1'), ObjectID(NamespaceID('n2'), 'o2')]),
        set([ObjectID(NamespaceID('n3'), 'o3'), ObjectID(NamespaceID('n4'), 'o4')]))

    assert storage.get_namespaces.call_args_list == [(([NamespaceID('n')],), {})]
    assert storage.find_mappings.call_args_list == [((ObjectID(NamespaceID('n'), 'o'),),
                                                     {'ns_filter': None})]


def test_get_mappings_with_filter():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    storage.get_namespaces.return_value = set([Namespace(NamespaceID('n'), False),
                                               Namespace(NamespaceID('n1'), False),
                                               Namespace(NamespaceID('n2'), False),
                                               Namespace(NamespaceID('n3'), False),
                                               Namespace(NamespaceID('n4'), False)])
    storage.find_mappings.return_value = (
        set([ObjectID(NamespaceID('n1'), 'o1'), ObjectID(NamespaceID('n2'), 'o2')]),
        set([ObjectID(NamespaceID('n3'), 'o3'), ObjectID(NamespaceID('n4'), 'o4')]))

    assert idm.get_mappings(
        ObjectID(NamespaceID('n'), 'o'), [NamespaceID('n1'), NamespaceID('n2'),
                                          NamespaceID('n4'), NamespaceID('n4')]) == (
        set([ObjectID(NamespaceID('n1'), 'o1'), ObjectID(NamespaceID('n2'), 'o2')]),
        set([ObjectID(NamespaceID('n3'), 'o3'), ObjectID(NamespaceID('n4'), 'o4')]))

    assert storage.get_namespaces.call_args_list == [(([NamespaceID('n'),
                                                        NamespaceID('n1'),
                                                        NamespaceID('n2'),
                                                        NamespaceID('n4'),
                                                        NamespaceID('n4')],), {})]
    assert storage.find_mappings.call_args_list == [((ObjectID(NamespaceID('n'), 'o'),),
                                                     {'ns_filter': [
                                                         NamespaceID('n1'),
                                                         NamespaceID('n2'),
                                                         NamespaceID('n4'),
                                                         NamespaceID('n4')]})]


def test_get_mappings_fail_None_inputs():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    oid = ObjectID(NamespaceID('n'), 'o')
    n = NamespaceID('n')

    fail_get_mappings(idm, None, set([n]), TypeError('oid cannot be None'))
    fail_get_mappings(idm, oid, set([n, None]), TypeError('None item in ns_filter'))


def test_get_mappings_fail_no_namespace():
    storage = create_autospec(IDMappingStorage, spec_set=True, instance=True)
    handlers = create_autospec(UserLookupSet, spec_set=True, instance=True)

    idm = IDMapper(handlers, set(), storage)

    storage.get_namespaces.side_effect = NoSuchNamespaceError('n3')

    fail_get_mappings(idm, ObjectID(NamespaceID('n'), 'o'), [
                      NamespaceID('n1'), NamespaceID('n2'),
                      NamespaceID('n4'), NamespaceID('n4')],
                      NoSuchNamespaceError('n3'))

    assert storage.get_namespaces.call_args_list == [(([NamespaceID('n'),
                                                        NamespaceID('n1'),
                                                        NamespaceID('n2'),
                                                        NamespaceID('n4'),
                                                        NamespaceID('n4')],), {})]


def fail_get_mappings(idm, oid, filters, expected):
    with raises(Exception) as got:
        idm.get_mappings(oid, filters)
    assert_exception_correct(got.value, expected)
