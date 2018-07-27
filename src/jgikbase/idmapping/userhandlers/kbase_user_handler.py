"""
A ID mapper service user handler for KBase (https://kbase.us) user accounts.
"""
from jgikbase.idmapping.core.user_handler import UserHandler
from jgikbase.idmapping.core.util import not_none
from jgikbase.idmapping.core.user import AuthsourceID, User, Username
from jgikbase.idmapping.core.tokens import Token
import requests


# WARNING - this is tested by mocking the requests library. The test suite never tests it against
# an actual KBase auth server. If you make changes, you must manually test that everything works
# against a live server.

class KBaseUserHandler(UserHandler):
    """
    A user handler for the ID mapping service.

    :ivar auth_url: The KBase authentication service url.
    """

    # TODO NOW caching

    _KBASE = AuthsourceID('kbase')

    def __init__(self, kbase_auth_url: str, kbase_token: Token) -> None:
        '''
        Create the handler.

        :param kbase_auth_url: The url for the KBase authentication service.
        :param kbase_token: A valid KBase user token. This is used for check the validity of
            user names.
        '''
        not_none(kbase_auth_url, 'kbase_auth_url')
        not_none(kbase_token, 'kbase_token')
        if not kbase_auth_url.endswith('/'):
            kbase_auth_url += '/'
        self.auth_url = kbase_auth_url
        self._token = kbase_token

    def get_authsource_id(self) -> AuthsourceID:
        return self._KBASE

    def _check_error(self, r):
        if r.status_code != 200:
            try:
                j = r.json()
            except Exception as e:  # @UnusedVariable
                raise IOError('Non-JSON response from KBase auth server, status code: ' +
                              str(r.status_code))
            # assume that if we get json then at least this is the auth server and we can
            # rely on the error structure.
            raise IOError('Error from KBase auth server: ' + j['error']['message'])
            # could check app codes here and respond appropriately,
            # don't worry about it for now.

    def get_user(self, token: Token) -> User:
        not_none(token, 'token')
        r = requests.get(self.auth_url + 'api/V2/token', headers={'Authorization': token.token})
        self._check_error(r)
        j = r.json()
        # other keys: expires, cachefor
        return User(self._KBASE, Username(j['user']))

    def is_valid_user(self, username: Username) -> bool:
        not_none(username, 'username')
        r = requests.get(self.auth_url + 'api/V2/users/?list=' + username.name,
                         headers={'Authorization': self._token.token})
        self._check_error(r)
        j = r.json()
        return len(j) == 1