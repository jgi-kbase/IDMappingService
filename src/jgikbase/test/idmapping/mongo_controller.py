"""
A controller for MongoDB useful for running tests.

Production use is not recommended.
"""

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

# semver parser
sver = semver.VersionInfo.parse


class MongoController:
    """
    The main MongoDB controller class.

    Attributes:
    port - the port for the MongoDB service.
    temp_dir - the location of the MongoDB data and logs.
    client - a pymongo client pointed at the server.
    db_version - the version of the mongod executable.
    index_version - the version of the indexes created by the mongod executable - 1 for < 3.4.0,
        2 otherwise.
    includes_system_indexes - true if system indexes will be included when listing database
        indexes, false otherwise.
    """

    def __init__(
        self, mongoexe: Path, root_temp_dir: Path, use_wired_tiger: bool = False
    ) -> None:
        """
        Create and start a new MongoDB database. An unused port will be selected for the server.

        :param mongoexe: The path to the MongoDB server executable (e.g. mongod) to run.
        :param root_temp_dir: A temporary directory in which to store MongoDB data and log files.
            The files will be stored inside a child directory that is unique per invocation.
        :param use_wired_tiger: For MongoDB versions > 3.0, specify that the Wired Tiger storage
            engine should be used. Setting this to true for other versions will cause an error.
        """
        if not mongoexe or not os.access(mongoexe, os.X_OK):
            raise TestException(
                "mongod executable path {} does not exist or is not executable.".format(
                    mongoexe
                )
            )
        if not root_temp_dir:
            raise ValueError("root_temp_dir is None")

        # make temp dirs
        root_temp_dir = root_temp_dir.absolute()
        os.makedirs(root_temp_dir, exist_ok=True)
        self.temp_dir = Path(
            tempfile.mkdtemp(prefix="MongoController-", dir=str(root_temp_dir))
        )
        data_dir = self.temp_dir.joinpath("data")
        os.makedirs(data_dir)

        self.port = test_utils.find_free_port()
        mongodb_ver = self.get_mongodb_version(mongoexe)

        command = [
            str(mongoexe),
            "--port",
            str(self.port),
            "--dbpath",
            str(data_dir),
        ]

        if sver(mongodb_ver) < sver('6.1.0'):
            command.extend(['--nojournal'])

        if use_wired_tiger:
            command.extend(["--storageEngine", "wiredTiger"])

        self._outfile = open(self.temp_dir.joinpath("mongo.log"), "w")

        self._proc = subprocess.Popen(
            command, stdout=self._outfile, stderr=subprocess.STDOUT
        )
        time.sleep(1)  # wait for server to start up

        try:
            self.client: MongoClient = MongoClient('localhost', self.port)
            # This line will raise an exception if the server is down
            server_info = self.client.server_info()
        except Exception as e:
            raise ValueError("MongoDB server is down") from e

        # get some info about the db
        self.db_version = server_info['version']
        self.index_version = 2 if (semver.compare(self.db_version, "3.4.0") >= 0) else 1
        self.includes_system_indexes = (
            semver.compare(self.db_version, "3.2.0") < 0 and not use_wired_tiger
        )

    def get_mongodb_version(self, mongoexe: Path) -> str:
        try:
            process = subprocess.Popen(
                [str(mongoexe), '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                version_line = stdout.decode().split('\n')[0]
                mongodb_version = version_line.split()[2][1:]
                return mongodb_version.strip()
            else:
                raise ValueError(f"Error: {stderr.decode()}")
        except Exception as e:
            raise ValueError("Failed to get MongoDB version") from e

    def destroy(self, delete_temp_files: bool) -> None:
        """
        Shut down the MongoDB server.

        :param delete_temp_files: delete all the MongoDB data files and logs generated during the
            test.
        """
        if self.client:
            self.client.close()
        if self._proc:
            self._proc.terminate()
        if self._outfile:
            self._outfile.close()
        if delete_temp_files and self.temp_dir:
            shutil.rmtree(self.temp_dir)

    def clear_database(self, db_name, drop_indexes=False):
        """
        Remove all data from a database.

        :param db_name: the name of the db to clear.
        :param drop_indexes: drop all indexes if true, retain indexes (which will be empty) if
            false.
        """
        if drop_indexes:
            self.client.drop_database(db_name)
        else:
            db = self.client[db_name]
            for name in db.list_collection_names():
                if not name.startswith("system."):
                    # don't drop collection since that drops indexes
                    db.get_collection(name).delete_many({})


def main():
    mongoexe = test_utils.get_mongo_exe()
    root_temp_dir = test_utils.get_temp_dir()

    mc = MongoController(mongoexe, root_temp_dir, False)
    print("port: " + str(mc.port))
    print("temp_dir: " + str(mc.temp_dir))
    print("db_version: " + mc.db_version)
    print("index_version: " + str(mc.index_version))
    print("includes_system_indexes: " + str(mc.includes_system_indexes))
    mc.client["foo"]["bar"].insert_one({"foo": "bar"})
    mc.clear_database("foo")
    input("press enter to shut down")
    mc.destroy(True)


if __name__ == "__main__":
    main()
