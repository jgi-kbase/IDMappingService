from jgikbase.idmapping.core.tokens import HashedToken
from pytest import fail
from jgikbase.test.idmapping.test_utils import assert_exception_correct


def test_hashed_token_init_pass():
    ht = HashedToken('foo')
    assert ht.token_hash == 'foo'


def test_hashed_token_init_fail():
    fail_hashed_token_init(None, ValueError('token_hash cannot be None'))
    fail_hashed_token_init('   \t    \n   ',
                           ValueError('token_hash cannot be None or whitespace only'))


def fail_hashed_token_init(htoken: str, expected: Exception):
    try:
        HashedToken(htoken)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)
