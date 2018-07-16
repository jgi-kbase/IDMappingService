from pathlib import Path
from jgikbase.test.idmapping.test_utils import TestException
import os
import tempfile
from jgikbase.test.idmapping import test_utils
import subprocess
import time
import shutil
from pymongo.mongo_client import MongoClient
import semver


class MongoController:

    def __init__(self, mongoexe: Path, root_temp_dir: Path, use_wired_tiger: bool=False) -> None:
        if not mongoexe or not os.access(mongoexe, os.X_OK):
            raise TestException('mongod executable path {} does not exist or is not executable.'
                                .format(mongoexe))
        if not root_temp_dir:
            raise ValueError('root_temp_dir is None')

        # make temp dirs
        root_temp_dir = root_temp_dir.absolute()
        os.makedirs(root_temp_dir, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix='MongoController-', dir=str(root_temp_dir)))
        data_dir = self.temp_dir.joinpath('data')
        os.makedirs(data_dir)

        self.port = test_utils.find_free_port()

        command = [str(mongoexe), '--port', str(self.port), '--dbpath', str(data_dir),
                   '--nojournal']
        if (use_wired_tiger):
            command.extend(['--storageEngine', 'wiredTiger'])

        self._outfile = open(self.temp_dir.joinpath('mongo.log'), 'w')

        self._proc = subprocess.Popen(command, stdout=self._outfile, stderr=subprocess.STDOUT)
        time.sleep(1)  # wait for server to start up
        self.client = MongoClient('localhost', self.port)
        # check that the server is up. See
        # https://api.mongodb.com/python/3.7.0/api/pymongo/mongo_client.html
        #    #pymongo.mongo_client.MongoClient
        self.client.admin.command('ismaster')

        # get some info about the db
        self.db_version = self.client.server_info()['version']
        self.index_version = 2 if (semver.compare(self.db_version, '3.4.0') >= 0) else 1
        self.includes_system_indexes = (semver.compare(self.db_version, '3.2.0') < 0
                                        and not use_wired_tiger)

    def destroy(self, delete_temp_files: bool) -> None:
        if self.client:
            self.client.close()
        if self._proc:
            self._proc.terminate()
        if self._outfile:
            self._outfile.close()
        if delete_temp_files and self.temp_dir:
            shutil.rmtree(self.temp_dir)

    def clear_database(self, db_name):
        db = self.client[db_name]
        for name in db.list_collection_names():
            if not name.startswith('system.'):
                # don't drop collection since that drops indexes
                db.get_collection(name).delete_many({})


def main():
    mongoexe = test_utils.get_mongo_exe()
    root_temp_dir = test_utils.get_temp_dir()

    mc = MongoController(mongoexe, root_temp_dir, False)
    print('port: ' + str(mc.port))
    print('temp_dir: ' + str(mc.temp_dir))
    print('db_version: ' + mc.db_version)
    print('index_version: ' + str(mc.index_version))
    print('includes_system_indexes: ' + str(mc.includes_system_indexes))
    mc.client['foo']['bar'].insert_one({'foo': 'bar'})
    mc.clear_database('foo')
    input('press enter to shut down')
    mc.destroy(True)


if __name__ == '__main__':
    main()
