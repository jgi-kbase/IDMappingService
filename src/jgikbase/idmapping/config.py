"""
Configuration handlers for the ID Mapping system.
"""
from typing import Dict, Optional
from pathlib import Path
import os
import configparser
# May want different configuration implementations based on the deployment environment.
# YAGNI for now.

# TODO CFG support user handler custom configs
# TODO CFG support which user handlers are enabled
# TODO CFG support which user handlers are allowed to specify admins


class IDMappingConfigError(Exception):
    """ Thrown when there's an error in the ID Mapping system configuration. """
    pass


class KBaseConfig:
    """
    Loads a configuration from a standard KBase-style deploy.cfg file (an ini file with only
    one section.) The configuration is contained in the `idmapping` section of the config file.

    The keys are:
    mongo-host
    mongo-db
    mongo-user
    mongo-pwd
    dont-trust-x-ip-headers

    The last key is optional and instructs the server to ignore the X-Real-IP and X-Forwarded-For
    headers if set to the string 'true'.

    :ivar mongo_host: the host of the MongoDB instance, including the port.
    :ivar mongo_db: the MongoDB database to use for the ID mapping service.
    :ivar mongo_user: the username to use with MongoDB, if any.
    :ivar mongo_pwd: the password to use with MongoDB, if any.
    :ivar ignore_ip_headers: True if the X-Real-IP and X-Forwarded-For headers should be ignored.
    """

    ENV_VAR_IDMAPPING = 'ID_MAPPING_CONFIG'
    """
    The first environment variable where the system will look for the path to the config file.
    """

    ENV_VAR_KB_DEP = 'KB_DEPLOYMENT_CONFIG'
    """
    The second environment variable where the system will look for the path to the config file.
    """

    CFG_SEC = 'idmapping'
    """ The section of the config file where the configuration is located. """

    _TEMP_KEY_CFG_FILE = 'temp-key-config-file'

    KEY_MONGO_HOST = 'mongo-host'
    """ The key corresponding to the value containing the MongoDB host. """

    KEY_MONGO_DB = 'mongo-db'
    """ The key corresponding to the value containing the MongoDB database. """

    KEY_MONGO_USER = 'mongo-user'
    """ The key corresponding to the value containing the MongoDB username. """

    KEY_MONGO_PWD = 'mongo-pwd'
    """ The key corresponding to the value containing the MongoDB user password. """

    KEY_IGNORE_IP_HEADERS = 'dont-trust-x-ip-headers'
    """
    The key corresponding to the value containing a boolean designating whether the X-Real_IP
    and X-Forwarded-For headers should be ignored. """

    _TRUE = 'true'

    def __init__(self, cfgfile: Path=None) -> None:
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
        self.mongo_user = self._get_string(self.KEY_MONGO_USER, cfg, False)
        mongo_pwd = self._get_string(self.KEY_MONGO_PWD, cfg, False)
        if bool(self.mongo_user) ^ bool(mongo_pwd):  # xor
            mongo_pwd = None
            raise IDMappingConfigError(
                ('Must provide both {} and {} params in config file ' +
                 '{} section {} if MongoDB authentication is to be used').format(
                     self.KEY_MONGO_USER, self.KEY_MONGO_PWD, cfg[self._TEMP_KEY_CFG_FILE],
                     self.CFG_SEC))
        self.mongo_pwd = mongo_pwd

    def _get_cfg(self, cfgfile: Path) -> Dict[str, str]:
        if not cfgfile.is_file():
            raise IDMappingConfigError('{} does not exist or is not a file'.format(cfgfile))
        config = configparser.ConfigParser()
        with cfgfile.open() as cfg:
            try:
                config.read_file(cfg)
            except configparser.Error as e:
                raise IDMappingConfigError('Error parsing config file {}: {}'.format(
                    cfgfile, e)) from e
        if self.CFG_SEC not in config:
            raise IDMappingConfigError('No section {} found in config file {}'.format(
                self.CFG_SEC, cfgfile))
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
        raise IDMappingConfigError('Could not find deployment configuration file from either ' +
                                   'permitted environment variable: {}, {}'.format(
                                       self.ENV_VAR_IDMAPPING, self.ENV_VAR_KB_DEP))

    def _get_string(self, param_name: str, config: Dict[str, str], raise_on_err: bool=True
                    ) -> Optional[str]:
        s = config.get(param_name)
        if s and s.strip():
            return s.strip()
        elif raise_on_err:
            raise IDMappingConfigError(
                'Required parameter {} not provided in configuration file {}, section {}'.format(
                    param_name, config[self._TEMP_KEY_CFG_FILE], self.CFG_SEC))
        else:
            return None
