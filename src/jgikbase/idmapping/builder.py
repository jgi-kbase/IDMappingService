"""
Contains code for building the core ID mapping code given a configuration.
"""
from jgikbase.idmapping.config import KBaseConfig
from jgikbase.idmapping.core.util import not_none
from jgikbase.idmapping.core.user_handler import LocalUserHandler, UserHandlerSet
from pymongo.mongo_client import MongoClient
from jgikbase.idmapping.storage.mongo.id_mapping_mongo_storage import IDMappingMongoStorage
from pymongo.errors import ConnectionFailure
from jgikbase.idmapping.core.mapper import IDMapper
from pathlib import Path
from jgikbase.idmapping.storage.id_mapping_storage import IDMappingStorage
from typing import cast


class IDMappingBuildException(Exception):
    """ Thrown when the build fails. """


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
        self.cfg = None
        self._storage = None

    def build_local_user_handler(self, cfgpath: Path) -> LocalUserHandler:
        """
        Build a local user handler.

        :param cfgpath: the the path to the build configuration file. The configuration is memoized
            and used in any future builds, and any other configurations are ignored.
        :raises IDMappingBuildException: if a build error occurs.
        :raises TypeError: if cfgpath is None.
        """
        not_none(cfgpath, 'cfgpath')
        self._set_cfg(cfgpath)
        self._build_storage()
        return LocalUserHandler(cast(IDMappingStorage, self._storage))

    def _set_cfg(self, cfg):
        if not self.cfg:
            self.cfg = KBaseConfig(cfg)

    def _build_storage(self):
        if not self._storage:
            if self.cfg.mongo_user:
                # NOTE this is currently only tested manually.
                client = MongoClient(self.cfg.mongo_host, authSource=self.cfg.mongo_db,
                                     username=self.cfg.mongo_user, password=self.cfg.mongo_pwd)
            else:
                client = MongoClient(self.cfg.mongo_host)
            try:
                # The ismaster command is cheap and does not require auth.
                client.admin.command('ismaster')
            except ConnectionFailure as e:
                raise IDMappingBuildException('Connection to database failed') from e
            db = client[self.cfg.mongo_db]
            self._storage = IDMappingMongoStorage(db)

    def build_id_mapping_system(self, cfgpath: Path) -> IDMapper:
        """
        Build the ID Mapping system.

        :param cfgpath: the the path to the build configuration file. The configuration is memoized
            and used in any future builds, and any other configurations are ignored.
        :raises IDMappingBuildException: if a build error occurs.
        :raises TypeError: if cfgpath is None.
        """
        # TODO BUILD get allowed auth sources from config
        # TODO BUILD build other user handlers
        not_none(cfgpath, 'cfgpath')
        self._set_cfg(cfgpath)
        luh = self.build_local_user_handler(cfgpath)
        uhs = UserHandlerSet(set([luh]))
        self._build_storage()
        return IDMapper(uhs, set(), cast(IDMappingStorage, self._storage))
