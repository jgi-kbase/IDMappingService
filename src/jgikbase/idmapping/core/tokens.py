"""
Classes representing authentication tokens.
"""

from jgikbase.idmapping.core.util import check_string


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
