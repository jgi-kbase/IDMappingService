"""
Contains code for building the core ID mapping code given a configuration.
"""

from jgikbase.idmapping.config import KBaseConfig
from jgikbase.idmapping.core.user_lookup import (
    LocalUserLookup,
    UserLookupSet,
    UserLookup,
    LookupInitializationError,
)
from pymongo.mongo_client import MongoClient
from jgikbase.idmapping.storage.mongo.id_mapping_mongo_storage import (
    IDMappingMongoStorage,
)
from pymongo.errors import ConnectionFailure
from jgikbase.idmapping.core.mapper import IDMapper
from pathlib import Path
from jgikbase.idmapping.core.user import AuthsourceID
import importlib
from jgikbase.idmapping.core.arg_check import not_none
from jgikbase.idmapping.storage.id_mapping_storage import IDMappingStorage
from typing import Dict, Set, Optional  # @UnusedImport pydev
from typing import cast


class IDMappingBuildException(Exception):
    """Thrown when the build fails."""


class _SometimesMyPyIsReallyStupid:  # pragma: no cover
    @staticmethod
    def build_lookup(config: Dict[str, str]) -> UserLookup:  # type: ignore[empty-body]
        pass


class IDMappingBuilder:
    """
    Contains methods for building the ID Mapping system.

    :ivar cfg: the build configuration. This is set after completing the first build, and future
        configurations are ignored.
    """

    # this is just tested via integration testing with other portions of the system.
    # There's not much to it.

    # TODO DB support sharded mongo?
    # TODO TEST integration test with authenticated db... ugh

    # may want to allow supporting other config types, YAGNI for now

    def __init__(self) -> None:
        """
        Create a builder.
        """

    def build_local_user_lookup(self, cfgpath: Optional[Path] = None) -> LocalUserLookup:
        """
        Build a local user lookup handler.

        :param cfgpath: the the path to the build configuration file. The configuration is memoized
            and used in any future builds, and any other configurations are ignored.
        :raises IDMappingBuildException: if a build error occurs.
        """
        self._set_cfg(cfgpath)
        return LocalUserLookup(self._build_storage())

    def _set_cfg(self, cfgpath) -> KBaseConfig:
        if not hasattr(self, "cfg"):
            self.cfg = KBaseConfig(cfgpath)
        return self.cfg

    def get_cfg(self, cfgpath: Optional[Path] = None) -> KBaseConfig:
        """
        Get the system configuration.

        :param cfgpath: the the path to the build configuration file. The configuration is memoized
            and used in any future builds, and any other configurations are ignored.
        """
        return self._set_cfg(cfgpath)

    def _build_storage(self) -> IDMappingStorage:
        if not hasattr(self, "_storage"):
            if self.cfg.mongo_user:
                # NOTE this is currently only tested manually.
                client: MongoClient = MongoClient(
                    self.cfg.mongo_host,
                    authSource=self.cfg.mongo_db,
                    username=self.cfg.mongo_user,
                    password=self.cfg.mongo_pwd,
                )
            else:
                client = MongoClient(self.cfg.mongo_host)
            try:
                # The ismaster command is cheap and does not require auth.
                client.admin.command("ismaster")
            except ConnectionFailure as e:
                raise IDMappingBuildException("Connection to database failed") from e
            db = client[self.cfg.mongo_db]  # type: ignore
            self._storage: IDMappingStorage = IDMappingMongoStorage(db)
        return self._storage

    def build_id_mapping_system(self, cfgpath: Optional[Path] = None) -> IDMapper:
        """
        Build the ID Mapping system.

        :param cfgpath: the the path to the build configuration file. The configuration is memoized
            and used in any future builds, and any other configurations are ignored.
        :raises IDMappingBuildException: if a build error occurs.
        """
        cfg = self._set_cfg(cfgpath)
        lookups: Set[UserLookup] = set()
        for asID in cfg.auth_enabled:
            if asID == LocalUserLookup.LOCAL:
                lookups.add(self.build_local_user_lookup(cfgpath))
            else:
                lookups.add(self.build_user_lookup(asID, *cfg.lookup_configs[asID]))
        return IDMapper(
            UserLookupSet(lookups), cfg.auth_admin_enabled, self._build_storage()
        )

    def build_user_lookup(
        self,
        config_authsource_id: AuthsourceID,
        factory_module: str,
        config: Dict[str, str],
    ) -> UserLookup:
        not_none(config_authsource_id, "config_authsource_id")
        not_none(factory_module, "factory_module")
        not_none(config, "config")
        try:
            mod = cast(
                _SometimesMyPyIsReallyStupid, importlib.import_module(factory_module)
            )
        except Exception as e:
            raise IDMappingBuildException(
                "Could not import module {}: {}".format(factory_module, str(e))
            ) from e
        try:
            lookup = mod.build_lookup(config)
        except LookupInitializationError as e:
            raise e
        except Exception as e:
            raise IDMappingBuildException(
                "Could not build module {}: {}".format(factory_module, str(e))
            ) from e
        if config_authsource_id != lookup.get_authsource_id():
            raise IDMappingBuildException(
                "User lookup authsource ID mismatch: configuration ID is {}, "
                "module reports ID {}".format(
                    config_authsource_id.id, lookup.get_authsource_id().id
                )
            )
        return lookup
