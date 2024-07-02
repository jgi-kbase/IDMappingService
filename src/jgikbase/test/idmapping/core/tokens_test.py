from jgikbase.idmapping.core.tokens import HashedToken, Token
from pytest import raises
from jgikbase.test.idmapping.test_utils import assert_exception_correct
from jgikbase.idmapping.core.errors import MissingParameterError
from jgikbase.idmapping.core import tokens
import base64


def test_hashed_token_init_pass():
    ht = HashedToken("foo")
    assert ht.token_hash == "foo"


def test_hashed_token_init_fail():
    fail_hashed_token_init(None, MissingParameterError("token_hash"))
    fail_hashed_token_init("   \t    \n   ", MissingParameterError("token_hash"))


def fail_hashed_token_init(htoken: str, expected: Exception):
    with raises(Exception) as got:
        HashedToken(htoken)
    assert_exception_correct(got.value, expected)


def test_hashed_token_equals():
    assert HashedToken("foo") == HashedToken("foo")
    assert HashedToken("foo") != HashedToken("bar")
    assert HashedToken("foo") != "foo"


def test_hashed_token_hash():
    # string hashes will change from instance to instance of the python interpreter, and therefore
    # tests can't be written that directly test the hash value. See
    # https://docs.python.org/3/reference/datamodel.html#object.__hash__
    assert hash(HashedToken("foo")) == hash(HashedToken("foo"))
    assert hash(HashedToken("bar")) == hash(HashedToken("bar"))
    assert hash(HashedToken("foo")) != hash(HashedToken("bar"))


def test_token_init_pass():
    t = Token("foo")
    assert t.token == "foo"


def test_token_init_fail():
    fail_token_init(None, MissingParameterError("token"))
    fail_token_init("   \t    \n   ", MissingParameterError("token"))


def fail_token_init(token: str, expected: Exception):
    with raises(Exception) as got:
        Token(token)
    assert_exception_correct(got.value, expected)


def test_hash_token():
    t = Token("foo")
    ht = t.get_hashed_token()
    assert (
        ht.token_hash
        == "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae"
    )


def test_token_equals():
    assert Token("foo") == Token("foo")
    assert Token("foo") != Token("bar")
    assert Token("foo") != "foo"


def test_token_hash():
    # string hashes will change from instance to instance of the python interpreter, and therefore
    # tests can't be written that directly test the hash value. See
    # https://docs.python.org/3/reference/datamodel.html#object.__hash__
    assert hash(Token("foo")) == hash(Token("foo"))
    assert hash(Token("bar")) == hash(Token("bar"))
    assert hash(Token("foo")) != hash(Token("bar"))


def test_generate_token():
    t = tokens.generate_token()
    assert is_base64(t.token) is True
    assert len(t.token) is 28


def is_base64(s: str):
    try:
        if base64.b64encode(base64.b64decode(s.encode())) == s.encode():
            return True
    except Exception as e:
        print(e)
    return False
