from jgikbase.idmapping.core.tokens import HashedToken
from pytest import fail
from jgikbase.test.idmapping.test_utils import assert_exception_correct
from jgikbase.idmapping.core.errors import MissingParameterError


def test_hashed_token_init_pass():
    ht = HashedToken('foo')
    assert ht.token_hash == 'foo'


def test_hashed_token_init_fail():
    fail_hashed_token_init(None, MissingParameterError('token_hash'))
    fail_hashed_token_init('   \t    \n   ', MissingParameterError('token_hash'))


def fail_hashed_token_init(htoken: str, expected: Exception):
    try:
        HashedToken(htoken)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)
