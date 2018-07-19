"""

Classes representing authentication tokens.

@author: gaprice@lbl.gov
"""

from jgikbase.idmapping.util.util import check_string


class HashedToken:
    """
    A token that has been hashed by a hashing algorithm.

    Attributes:

    token_hash - the token hash.
    """

    # TODO NOW

    def __init__(self, token_hash: str) -> None:
        """
        Create a hashed token.

        :param token_hash: the hash of the token.
        """
        check_string(token_hash, 'token_hash')
        self.token_hash = token_hash
