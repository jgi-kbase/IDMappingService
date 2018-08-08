from jgikbase.idmapping.core.user_lookup import UserLookup  # pragma: no cover
from jgikbase.idmapping.core.user import AuthsourceID, User, Username  # pragma: no cover
from jgikbase.idmapping.core.tokens import Token  # pragma: no cover
from typing import Optional, Tuple  # pragma: no cover
from jgikbase.idmapping.core.arg_check import not_none  # pragma: no cover
import requests  # pragma: no cover
from jgikbase.idmapping.core.errors import InvalidTokenError  # pragma: no cover
from typing import Dict


# This is a prototype for interfacing with the JGI authentication system, Caliban.
# Currently it has no automated tests.
# The reasons it is a prototype are:
# 1) JGI uses integer user IDs rather than user names as immutable IDs, which are not very
#    readable. Maybe this is ok and the UI should be responsible for displaying readable
#    user names, but it needs some discussion / thought.
# 2) JGI accounts can be merged, which means a single account can have multiple user IDs.
#    The prototype does not account for that at this point and as such if a user merges one
#    account into another, they will lose access to the data linked to the first account.
#    get_user and is_valid_user should reject merged user accounts.
# 3) There is no way to specify which users are system admins. This probably isn't possible
#    without changes on the JGI side.
# 4) It has no docs.
# 5) It's a Q&D implementation and needs proper input checking and exception handling.

class JGIUserLookup(UserLookup):  # pragma: no cover

    _JGI = AuthsourceID('jgi')

    def __init__(self, jgi_auth_url: str) -> None:
        if not jgi_auth_url.endswith('/'):
            jgi_auth_url += '/'
        self.auth_url = jgi_auth_url

    def get_authsource_id(self) -> AuthsourceID:
        return self._JGI

    def get_user(self, token: Token) -> Tuple[User, bool, Optional[int], Optional[int]]:
        not_none(token, 'token')
        # yes the token is in the url
        r = requests.get(self.auth_url + 'api/sessions/' + token.token + '.json')
        if 400 <= r.status_code <= 499:
            raise InvalidTokenError('JGI auth server reported token is invalid: ' +
                                    str(r.status_code))
        if 500 <= r.status_code <= 599:
            raise IOError('JGI auth server reported an internal error: ' + str(r.status_code))
        sres = r.json()
        return (User(self._JGI, Username(str(sres['user']['id']))), False, None, 300)

    def is_valid_user(self, username: Username) -> Tuple[bool, Optional[int], Optional[int]]:
        not_none(username, 'username')
        r = requests.get(self.auth_url + 'api/users/' + username.name + '.json')
        if 200 <= r.status_code <= 299:
            return (True, None, 3600)
        if r.status_code == 410:  # Uses Gone to denote no such user
            return (False, None, 3600)
        raise IOError('Unexpected error from JGI server: ' + str(r.status_code))


def build_lookup(config: Dict[str, str]) -> UserLookup:  # pragma: no cover
    return JGIUserLookup(config['url'])
