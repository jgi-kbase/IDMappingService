"""
Classes representing authentication tokens.
"""

from jgikbase.idmapping.core.util import check_string
import secrets
import hashlib
import base64


class HashedToken:
    """
    A token that has been hashed by a hashing algorithm.

    :ivar token_hash: the token hash.
    """

    def __init__(self, token_hash: str) -> None:
        """
        Create a hashed token.

        :param token_hash: the hash of the token.
        :raises MissingParameterError: if the token hash is None or whitespace only.
        """
        check_string(token_hash, 'token_hash')
        self.token_hash = token_hash

    def __eq__(self, other):
        if type(other) is type(self):
            return other.token_hash == self.token_hash
        return False

    def __hash__(self):
        return hash((self.token_hash,))


class Token:
    """
    A token.

    :ivar token: the token.
    """

    def __init__(self, token: str) -> None:
        '''
        Create a token.
        :param token: the token string.
        :raises MissingParameterError: if the token is None or whitespace only.
        '''
        check_string(token, "token")
        self.token = token

    def get_hashed_token(self) -> HashedToken:
        '''
        Returns a sha256 hash of this token represented as a hex string.
        '''
        return HashedToken(hashlib.sha256(self.token.encode()).hexdigest())

    def __eq__(self, other):
        if type(other) is type(self):
            return other.token == self.token
        return False

    def __hash__(self):
        return hash((self.token,))


def generate_token() -> Token:
    '''
    Generates a 160 bit token in base64 format.
    '''
    return Token(base64.b64encode(secrets.token_bytes(20)).decode())
