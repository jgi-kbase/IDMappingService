from jgikbase.idmapping.core.tokens import HashedToken, Token
from pytest import fail
from jgikbase.test.idmapping.test_utils import assert_exception_correct
from jgikbase.idmapping.core.errors import MissingParameterError
from jgikbase.idmapping.core import tokens
import base64


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


def test_token_init_pass():
    t = Token('foo')
    assert t.token == 'foo'


def test_token_init_fail():
    fail_token_init(None, MissingParameterError('token'))
    fail_token_init('   \t    \n   ', MissingParameterError('token'))


def fail_token_init(token: str, expected: Exception):
    try:
        Token(token)
        fail('expected exception')
    except Exception as got:
        assert_exception_correct(got, expected)


def test_hash_token():
    t = Token('foo')
    ht = t.get_hashed_token()
    assert ht.token_hash == '2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae'


def test_generate_token():
    t = tokens.generate_token()
    assert isBase64(t.token) is True
    assert len(t.token) is 28


def isBase64(s):
    try:
        if base64.b64encode(base64.b64decode(s)) == s:
            return True
    except Exception as e:
        print(e)
    return False
