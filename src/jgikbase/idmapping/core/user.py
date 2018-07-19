"""
ID Mapping system user classes.

"""
from jgikbase.idmapping.util.util import not_none, check_string


class Authsource:
    """
    An authorization source for a user.

    Attributes:
    authsource - the name of the authentication source.
    """

    _legal_chars = 'a-z'
    _max_len = 20

    def __init__(self, authsource: str) -> None:
        '''
        Create an authorization source.

        :param authsource: A string identifier for the authorization source, consisting only of
            lowercase ASCII letters and no longer than 20 characters.
        '''
        check_string(authsource, 'authsource', self._legal_chars, self._max_len)
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

    _legal_chars = 'a-z0-9'
    _max_len = 100

    def __init__(self, authsource: Authsource, username: str) -> None:
        """
        Create a new user.

        :param authsource: The authentication source for the user.
        :param username: The name of the user matching the regex ^[a-z][a-z0-9]+$ and no longer
            than 100 characters.
        """
        not_none(authsource, 'authsource')
        check_string(username, 'username', self._legal_chars, self._max_len)
        if not username[0].isalpha():
            # TODO EXCEP change to package specific exception
            raise ValueError('username {} must start with a letter'.format(username))
        self.authsource = authsource
        self.username = username
