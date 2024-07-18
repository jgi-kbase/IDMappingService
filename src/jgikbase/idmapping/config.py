"""
Configuration handlers for the ID Mapping system.
"""

from typing import Dict, Optional, Set, Tuple
from pathlib import Path
import os
import configparser
from jgikbase.idmapping.core.user import AuthsourceID
from jgikbase.idmapping.core.errors import MissingParameterError
from jgikbase.idmapping.core.user_lookup import LocalUserLookup

# May want different configuration implementations based on the deployment environment.
# YAGNI for now.


class IDMappingConfigError(Exception):
    """Thrown when there's an error in the ID Mapping system configuration."""

    pass


class KBaseConfig:
    """
    Loads a configuration from a standard KBase-style deploy.cfg file (an ini file with only
    one section.) The configuration is contained in the `idmapping` section of the config file.

    The keys are:
    mongo-host
    mongo-db
    mongo-user (optional)
    mongo-pwd (optional)
    mongo-retrywrites (optional)
    authentication-enabled (optional)
    authentication-admin-enabled (optional)
    keys specific to each authentication source. See the example deploy.cfg file in this repo
    or the class variables.
    dont-trust-x-ip-headers (optional)

    The last key instructs the server to ignore the X-Real-IP and X-Forwarded-For
    headers if set to the string 'true'.

    :ivar mongo_host: the host of the MongoDB instance, including the port.
    :ivar mongo_db: the MongoDB database to use for the ID mapping service.
    :ivar mongo_user: the username to use with MongoDB, if any.
    :ivar mongo_pwd: the password to use with MongoDB, if any.
    :ivar mongo_retrywrites: whether to enable retryWrites parameter with MongoDB.
    :ivar auth_enabled: the set of authentication sources that are enabled.
    :ivar auth_admin_enabled: the set of authentication sources that are trusted to define
        system administrators.
    :ivar ignore_ip_headers: True if the X-Real-IP and X-Forwarded-For headers should be ignored.
    :ivar lookup_configs: the configurations for the user lookup instances. This is a dict
        of :class:`jgikbase.idmapping.core.user.AuthsourceID` to the configuration for the lookup
        instance for that authsource. The configuration is a tuple where the first entry is a
        string denoting the module containing the factory method used to create the lookup
        instance. The second entry is a str -> str dict containing the configuration for the
        lookup instance.
    """

    ENV_VAR_IDMAPPING = "ID_MAPPING_CONFIG"
    """
    The first environment variable where the system will look for the path to the config file.
    """

    ENV_VAR_KB_DEP = "KB_DEPLOYMENT_CONFIG"
    """
    The second environment variable where the system will look for the path to the config file.
    """

    CFG_SEC = "idmapping"
    """ The section of the config file where the configuration is located. """

    _TEMP_KEY_CFG_FILE = "temp-key-config-file"

    KEY_MONGO_HOST = "mongo-host"
    """ The key corresponding to the value containing the MongoDB host. """

    KEY_MONGO_DB = "mongo-db"
    """ The key corresponding to the value containing the MongoDB database. """

    KEY_MONGO_USER = "mongo-user"
    """ The key corresponding to the value containing the MongoDB username. """

    KEY_MONGO_PWD = "mongo-pwd"  # nosec
    """ The key corresponding to the value containing the MongoDB user password. """

    KEY_MONGO_RETRYWRITES = "mongo-retrywrites"
    """ The key corresponding to the value containing the MongoDB retrywrites. """

    KEY_AUTH_ENABLED = "authentication-enabled"
    """
    The key corresponding to the value containing a comma separated list of authentication sources
    that should be enabled on system start up.
    """

    KEY_AUTH_ADMIN_ENABLED = "authentication-admin-enabled"
    """
    The key corresponding to the value containing a comma separated list of authentication sources
    that are trusted to define system administrators.
    """

    KEY_IGNORE_IP_HEADERS = "dont-trust-x-ip-headers"
    """
    The key corresponding to the value containing a boolean designating whether the X-Real_IP
    and X-Forwarded-For headers should be ignored. """

    AUTH_PREFIX = "auth-source-"
    """ The prefix for keys for specific authentication sources. """

    FACTORY_MODULE = "-factory-module"
    """
    The suffix for the key for a specific authentication source that defines the python
    module containing the factory for the user lookup instance.
    """

    INIT = "-init-"
    """
    The portion of the key after the authentication source name that defines the key as
    a key-value configuration item.
    """

    _TRUE = "true"

    def __init__(self, cfgfile: Optional[Path] = None) -> None:
        """
        Load the configuration.

        :param cfgfile: the path to the configuration file. If not provided, the path will be
            looked up in the environment variables, in order of precedence, ID_MAPPING_CONFIG and
            KB_DEPLOYMENT_CONFIG.
        """
        if not cfgfile:
            cfgfile = self._get_cfg_from_env()
        cfg = self._get_cfg(cfgfile)
        self.ignore_ip_headers = self._TRUE == cfg.get(self.KEY_IGNORE_IP_HEADERS)
        self.mongo_host = self._get_string(self.KEY_MONGO_HOST, cfg)
        self.mongo_db = self._get_string(self.KEY_MONGO_DB, cfg)
        self.mongo_retrywrites = self._TRUE == self._get_string(self.KEY_MONGO_RETRYWRITES, cfg, False)
        self.mongo_user = self._get_string(self.KEY_MONGO_USER, cfg, False)
        mongo_pwd = self._get_string(self.KEY_MONGO_PWD, cfg, False)
        if bool(self.mongo_user) ^ bool(mongo_pwd):  # xor
            mongo_pwd = None
            raise IDMappingConfigError(
                (
                    "Must provide both {} and {} params in config file "
                    + "{} section {} if MongoDB authentication is to be used"
                ).format(
                    self.KEY_MONGO_USER,
                    self.KEY_MONGO_PWD,
                    cfg[self._TEMP_KEY_CFG_FILE],
                    self.CFG_SEC,
                )
            )
        self.mongo_pwd = mongo_pwd
        self.auth_enabled = self._get_authsource_ids(self.KEY_AUTH_ENABLED, cfg)
        self.auth_admin_enabled = self._get_authsource_ids(
            self.KEY_AUTH_ADMIN_ENABLED, cfg
        )
        self.lookup_configs = self._get_lookup_configs(cfg)

    def _get_cfg(self, cfgfile: Path) -> Dict[str, str]:
        if not cfgfile.is_file():
            raise IDMappingConfigError(
                "{} does not exist or is not a file".format(cfgfile)
            )
        config = configparser.ConfigParser()
        with cfgfile.open() as cfg:
            try:
                config.read_file(cfg)
            except configparser.Error as e:
                raise IDMappingConfigError(
                    "Error parsing config file {}: {}".format(cfgfile, e)
                ) from e
        if self.CFG_SEC not in config:
            raise IDMappingConfigError(
                "No section {} found in config file {}".format(self.CFG_SEC, cfgfile)
            )
        sec = config[self.CFG_SEC]
        # a section is not a real map and is missing methods
        c = {x: sec[x] for x in sec.keys()}
        c[self._TEMP_KEY_CFG_FILE] = str(cfgfile)
        return c

    def _get_cfg_from_env(self) -> Path:
        if os.environ.get(self.ENV_VAR_IDMAPPING):
            return Path(os.environ[self.ENV_VAR_IDMAPPING])
        if os.environ.get(self.ENV_VAR_KB_DEP):
            return Path(os.environ[self.ENV_VAR_KB_DEP])
        raise IDMappingConfigError(
            "Could not find deployment configuration file from either "
            + "permitted environment variable: {}, {}".format(
                self.ENV_VAR_IDMAPPING, self.ENV_VAR_KB_DEP
            )
        )

    def _get_string(
        self, param_name: str, config: Dict[str, str], raise_on_err: bool = True
    ) -> Optional[str]:
        s = config.get(param_name)
        if s and s.strip():
            return s.strip()
        elif raise_on_err:
            raise IDMappingConfigError(
                "Required parameter {} not provided in configuration file {}, section {}".format(
                    param_name, config[self._TEMP_KEY_CFG_FILE], self.CFG_SEC
                )
            )
        else:
            return None

    def _get_authsource_ids(
        self, param_name: str, config: Dict[str, str]
    ) -> Set[AuthsourceID]:
        s = self._get_string(param_name, config, False)
        ret: Set[AuthsourceID] = set()
        if not s:
            return ret
        ids = s.split(",")
        for id_ in ids:
            try:
                ret.add(AuthsourceID(id_.strip()))
            except MissingParameterError as e:
                raise IDMappingConfigError(
                    (
                        "Parameter {} in configuration file {}, section {}, "
                        "has whitespace-only entry"
                    ).format(
                        param_name,
                        config[self._TEMP_KEY_CFG_FILE],
                        self.CFG_SEC,
                    )
                ) from e
            except Exception as e:
                raise IDMappingConfigError(
                    "Parameter {} in configuration file {}, section {}, is invalid: {}".format(
                        param_name,
                        config[self._TEMP_KEY_CFG_FILE],
                        self.CFG_SEC,
                        str(e),
                    )
                ) from e
        return ret

    def _get_lookup_configs(
        self, cfg
    ) -> Dict[AuthsourceID, Tuple[str, Dict[str, str]]]:
        ret = {}
        for asID in self.auth_enabled:
            if asID == LocalUserLookup.LOCAL:
                continue
            prefix = self.AUTH_PREFIX + asID.id
            factory = None
            lookupcfg = {}
            for key, val in cfg.items():
                if key.startswith(prefix):
                    if key == prefix + self.FACTORY_MODULE:
                        factory = val.strip()
                    elif key.startswith(prefix + self.INIT):
                        lookupcfg[key[len(prefix + self.INIT):]] = val.strip()
                    else:
                        raise IDMappingConfigError(
                            "Unexpected parameter {} in configuration file {}, section {}".format(
                                key, cfg[self._TEMP_KEY_CFG_FILE], self.CFG_SEC
                            )
                        )
            if not factory:
                raise IDMappingConfigError(
                    "Required parameter {} not provided in configuration file {}, "
                    "section {}".format(
                        prefix + self.FACTORY_MODULE,
                        cfg[self._TEMP_KEY_CFG_FILE],
                        self.CFG_SEC,
                    )
                )
            ret[asID] = (factory, lookupcfg)
        return ret
