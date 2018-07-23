"""
ID Mapping system user classes.

Attributes:
LOCAL - a local authentication source (see :class:`jgikbase.idmapping.core.user.AuthsourceID`.

"""
from jgikbase.idmapping.util.util import not_none, check_string


class AuthsourceID:
    """
    An identifier for an authentication source for a user.

    An authentication source is any server, program, or agent that can give you back a
    username when it is given a secret token.

    Attributes:
    authsource - the ID of the authentication source.
    LOCAL - a string designating a local authentication source.
    """

    LOCAL = 'local'

    _LEGAL_CHARS = 'a-z'
    _MAX_LEN = 20

    def __init__(self, authsource: str) -> None:
        '''
        Create an authentication source identifier.

        :param authsource: A string identifier for the authentication source, consisting only of
            lowercase ASCII letters and no longer than 20 characters.
        '''
        check_string(authsource, 'authsource', self._LEGAL_CHARS, self._MAX_LEN)
        self.authsource = authsource

    def __eq__(self, other):
        if type(other) is type(self):
            return other.authsource == self.authsource
        return False


LOCAL = AuthsourceID(AuthsourceID.LOCAL)


class User:
    """
    A user for the ID mapping system. Consists of a authentication source and a user name.
    The authentication source determines how the ID service should authenticate a user given
    a secret.

    Attributes:
    authsource - the authentication source.
    username - the user name.
    """

    _LEGAL_CHARS = 'a-z0-9'
    _MAX_LEN = 100

    def __init__(self, authsource: AuthsourceID, username: str) -> None:
        """
        Create a new user.

        :param authsource: The authentication source for the user.
        :param username: The name of the user matching the regex ^[a-z][a-z0-9]+$ and no longer
            than 100 characters.
        """
        not_none(authsource, 'authsource')
        check_string(username, 'username', self._LEGAL_CHARS, self._MAX_LEN)
        if not username[0].isalpha():
            # TODO EXCEP change to package specific exception
            raise ValueError('username {} must start with a letter'.format(username))
        self.authsource = authsource
        self.username = username
