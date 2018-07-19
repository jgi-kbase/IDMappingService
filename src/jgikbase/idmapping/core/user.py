"""
ID Mapping system user classes.

"""
from jgikbase.idmapping.util.util import not_none


class AuthsourceID:
    """
    An identifier for an authorization source for a user.

    Attributes:
    authsource - the ID of the authentication source.
    """

    def __init__(self, authsource: str) -> None:
        not_none(authsource, 'authsource')
        self.authsource = authsource


class User:
    """
    A user for the ID mapping system. Consists of a authentication source and a user name.
    The authentication source determines how the ID service should authenticate a user given
    a secret.

    Attributes:
    authsource - the authentication source.
    username - the user name.
    """

    def __init__(self, authsource: AuthsourceID, username: str) -> None:
        """
        Create a new user.

        :param authsource: The authentication source for the user.
        :param username: The name of the user.
        """
        not_none(authsource, 'authsource')
        not_none(username, 'username')
        self.authsource = authsource
        self.username = username
