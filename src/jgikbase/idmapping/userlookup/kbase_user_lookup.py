"""
A ID mapper service user lookup handler for KBase (https://kbase.us) user accounts.
"""
from jgikbase.idmapping.core.user_lookup import UserLookup, LookupInitializationError
from jgikbase.idmapping.core.arg_check import not_none
from jgikbase.idmapping.core.user import AuthsourceID, User, Username
from jgikbase.idmapping.core.tokens import Token
import requests
from jgikbase.idmapping.core.errors import InvalidTokenError
from typing import Tuple, Optional, Dict
import logging


# WARNING - this is tested by mocking the requests library. The test suite never tests it against
# an actual KBase auth server. If you make changes, you must manually test that everything works
# against a live server.

class KBaseUserLookup(UserLookup):
    """
    A user lookup handler for the ID mapping service.

    :ivar auth_url: The KBase authentication service url.
    """

    _KBASE = AuthsourceID('kbase')

    def __init__(self, kbase_auth_url: str, kbase_token: Token, kbase_system_admin: str) -> None:
        '''
        Create the lookup handler.

        :param kbase_auth_url: The url for the KBase authentication service.
        :param kbase_token: A valid KBase user token. This is used for checking the validity of
            user names.
        :param kbase_system_admin: the custom role the user must possess in the KBase auth
            system to be considered an admin of the ID mapping service.
        '''
        not_none(kbase_auth_url, 'kbase_auth_url')
        not_none(kbase_token, 'kbase_token')
        not_none(kbase_system_admin, 'kbase_system_admin')
        if not kbase_auth_url.endswith('/'):
            kbase_auth_url += '/'
        self.auth_url = kbase_auth_url
        self._token = kbase_token
        self._kbase_system_admin = kbase_system_admin
        r = requests.get(self.auth_url, headers={'Accept': 'application/json'})
        self._check_error(r)
        missing_keys = {'version', 'gitcommithash', 'servertime'} - r.json().keys()
        if missing_keys:
            raise IOError('{} does not appear to be the KBase auth server. '.format(
                            kbase_auth_url) +
                          'The root JSON response does not contain the expected keys {}'.format(
                              sorted(missing_keys)))
        # could use the server time to adjust for clock skew
        # also could check token is valid and the system admin role exists
        # probably not worth the trouble

    def get_authsource_id(self) -> AuthsourceID:
        return self._KBASE

    def _check_error(self, r):
        if r.status_code != 200:
            try:
                j = r.json()
            except Exception:
                err = ('Non-JSON response from KBase auth server, status code: ' +
                       str(r.status_code))
                logging.getLogger(__name__).info('%s, response:\n%s', err, r.text)
                raise IOError(err)
            # assume that if we get json then at least this is the auth server and we can
            # rely on the error structure.
            if j['error']['apperror'] == 'Invalid token':
                raise InvalidTokenError('KBase auth server reported token is invalid.')
            # don't really see any other error codes we need to worry about - maybe disabled?
            # worry about it later.
            raise IOError('Error from KBase auth server: ' + j['error']['message'])

    def get_user(self, token: Token) -> Tuple[User, bool, Optional[int], Optional[int]]:
        not_none(token, 'token')
        r = requests.get(self.auth_url + 'api/V2/token', headers={'Authorization': token.token})
        self._check_error(r)
        tokenres = r.json()
        r = requests.get(self.auth_url + 'api/V2/me', headers={'Authorization': token.token})
        self._check_error(r)
        mres = r.json()
        return (User(self._KBASE, Username(tokenres['user'])),
                self._kbase_system_admin in mres['customroles'],
                tokenres['expires'] // 1000,
                tokenres['cachefor'] // 1000)

    def is_valid_user(self, username: Username) -> Tuple[bool, Optional[int], Optional[int]]:
        not_none(username, 'username')
        r = requests.get(self.auth_url + 'api/V2/users/?list=' + username.name,
                         headers={'Authorization': self._token.token})
        self._check_error(r)
        j = r.json()
        return (len(j) == 1, None, 3600)


def build_lookup(config: Dict[str, str]) -> UserLookup:
    """
    Build a KBase user lookup instance.

    :params config: A dictionary containing the keys 'url' for the KBase auth server url,
        'token' for a valid KBase token, and 'admin-role' for the KBase auth server custom
        role the user must possess in order to be an admin of the ID Mapping system.
    """
    err = 'kbase user lookup handler requires {} configuration item'
    if 'url' not in config:
        raise LookupInitializationError(err.format('url'))
    if 'token' not in config:
        raise LookupInitializationError(err.format('token'))
    if 'admin-role' not in config:
        raise LookupInitializationError(err.format('admin-role'))
    return KBaseUserLookup(config['url'], Token(config['token']), config['admin-role'])
