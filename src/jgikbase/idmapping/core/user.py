"""
ID Mapping system user classes.
"""
from jgikbase.idmapping.core.util import not_none, check_string
from jgikbase.idmapping.core.errors import IllegalUsernameError, IllegalParameterError


class AuthsourceID:
    """
    An identifier for an authentication source for a user.

    An authentication source is any server, program, or agent that can give you back a
    username when it is given a secret token.

    :ivar id: the ID of the authentication source.
    """

    _LEGAL_CHARS = 'a-z'
    _MAX_LEN = 20

    def __init__(self, id_: str) -> None:
        '''
        Create an authentication source identifier.

        :param id_: A string identifier for the authentication source, consisting only of
            lowercase ASCII letters and no longer than 20 characters.
        :raises MissingParameterError: if the id is None or whitespace only.
        :raises IllegalParameterError: if the id does not match the requirements.
        '''
        check_string(id_, 'authsource id', self._LEGAL_CHARS, self._MAX_LEN)
        self.id = id_

    def __eq__(self, other):
        if type(other) is type(self):
            return other.id == self.id
        return False

    def __hash__(self):
        return hash((self.id,))


class Username:
    """
    The name of a user.

    :ivar name: the username.
    """

    def __init__(self, username: str) -> None:
        """
        Create a new user name.

        :param username: The name of the user matching the regex ^[a-z][a-z0-9]+$ and no longer
            than 100 characters.
        :raises MissingParameterError: if the user name is None or whitespace only.
        :raises IllegalUsernameError: if the user name does not meet the requirements.
        """
        try:
            check_string(username, 'username', 'a-z0-9', 100)
        except IllegalParameterError as e:
            raise IllegalUsernameError(e.message) from e
        if not username[0].isalpha():
            raise IllegalUsernameError('username {} must start with a letter'.format(username))
        self.name = username

    def __eq__(self, other):
        if type(other) is type(self):
            return other.name == self.name
        return False

    def __hash__(self):
        return hash((self.name,))


class User:
    """
    A user for the ID mapping system. Consists of a authentication source and a user name.
    The authentication source determines how the ID service should authenticate a user given
    a secret.

    :ivar authsource_id: the authentication source.
    :ivar username: the user name.
    """

    def __init__(self, authsource_id: AuthsourceID, username: Username) -> None:
        """
        Create a new user.

        :param authsource_id: The authentication source for the user.
        :param username: The name of the user.
        :raises TypeError: if any of the arguments are None.
        """
        not_none(authsource_id, 'authsource_id')
        not_none(username, 'username')
        self.authsource_id = authsource_id
        self.username = username

    def __eq__(self, other):
        if type(other) is type(self):
            return other.authsource_id == self.authsource_id and other.username == self.username
        return False

    def __hash__(self):
        return hash((self.authsource_id, self.username))
