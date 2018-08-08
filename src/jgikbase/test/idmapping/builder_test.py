from jgikbase.idmapping.builder import IDMappingBuilder, IDMappingBuildException
from jgikbase.idmapping.core.user import AuthsourceID
from jgikbase.test.idmapping.user_lookup_test_module import FakeUserLookup
from pytest import raises
from jgikbase.test.idmapping.test_utils import assert_exception_correct
from jgikbase.idmapping.core.user_lookup import LookupInitializationError

# this tests the parts of the builder that don't require starting up mongoDB. Those
# are tested in integration tests.

# For now, that means the UserLookup loading code.

TEST_MODULE = 'jgikbase.test.idmapping.user_lookup_test_module'


def test_build_user_lookup():
    b = IDMappingBuilder()
    ul = b.build_user_lookup(AuthsourceID('foo'), TEST_MODULE, {'asid': 'foo'})
    assert ul.cfg == {'asid': 'foo'}
    assert isinstance(ul, FakeUserLookup) is True


def test_build_user_lookup_fail_input():
    a = AuthsourceID('i')
    fail_build_user_lookup(None, 'm', {}, TypeError('config_authsource_id cannot be None'))
    fail_build_user_lookup(a, None, {}, TypeError('factory_module cannot be None'))
    fail_build_user_lookup(a, 'm', None, TypeError('config cannot be None'))


def test_build_user_lookup_fail_import():
    m = 'jgikbase.test.idmapping.this_module_does_not_exist'
    fail_build_user_lookup(AuthsourceID('i'), m, {}, IDMappingBuildException(
            'Could not import module ' + m + ": No module named '" + m + "'"))


def test_build_user_lookup_fail_init():
    fail_build_user_lookup(AuthsourceID('i'), TEST_MODULE, {'initfail': 'nope, sorry'},
                           LookupInitializationError('nope, sorry'))


def test_build_user_lookup_fail_init_unexpected():
    fail_build_user_lookup(AuthsourceID('i'), TEST_MODULE, {'initunex': 'well crap'},
                           IDMappingBuildException('Could not build module ' + TEST_MODULE +
                                                   ': well crap'))


def test_build_user_lookup_fail_id_mismatch():
    fail_build_user_lookup(
        AuthsourceID('i'), TEST_MODULE, {'asid': 'j'}, IDMappingBuildException(
            'User lookup authsource ID mismatch: configuration ID is i, module reports ID j'))


def fail_build_user_lookup(asid, module, cfg, expected):
    with raises(Exception) as got:
        IDMappingBuilder().build_user_lookup(asid, module, cfg)
    assert_exception_correct(got.value, expected)
