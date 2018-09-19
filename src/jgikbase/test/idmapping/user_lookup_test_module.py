from jgikbase.idmapping.core.user_lookup import UserLookup, LookupInitializationError
from jgikbase.idmapping.core.user import AuthsourceID


class FakeUserLookup(UserLookup):

    def __init__(self, cfg):
        if 'initfail' in cfg:
            raise LookupInitializationError(cfg['initfail'])
        if 'initunex' in cfg:
            raise ValueError(cfg['initunex'])
        self.cfg = cfg

    def get_authsource_id(self) -> AuthsourceID:
        return AuthsourceID(self.cfg['asid'])


def build_lookup(cfg):
    return FakeUserLookup(cfg)
