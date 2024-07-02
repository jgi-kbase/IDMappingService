import os
import socket
from contextlib import closing
from pathlib import Path
import configparser
from logging import Formatter
from typing import List  # @UnusedImport pydev
from logging import LogRecord  # @UnusedImport pydev
import time
import re

MONGO_EXE = "test.mongo.exe"
TEST_TEMP_DIR = "test.temp.dir"
MONGO_USE_WIRED_TIGER = "test.mongo.wired_tiger"
KEEP_TEMP_DIR = "test.temp.dir.keep"

TEST_CONFIG_FILE_SECTION = "idmappingservicetest"

TEST_FILE_LOC_ENV_KEY = "IDMAP_TEST_FILE"

_CONFIG = None


def get_mongo_exe() -> Path:
    return Path(os.path.abspath(_get_test_property(MONGO_EXE)))


def get_temp_dir() -> Path:
    return Path(os.path.abspath(_get_test_property(TEST_TEMP_DIR)))


def get_use_wired_tiger() -> bool:
    return _get_test_property(MONGO_USE_WIRED_TIGER) == "true"


def get_delete_temp_files() -> bool:
    return _get_test_property(KEEP_TEMP_DIR) != "true"


def _get_test_config_file_path() -> Path:
    p = os.environ.get(TEST_FILE_LOC_ENV_KEY)
    if not p:
        raise TestException(
            "Can't find key {} in environment".format(TEST_FILE_LOC_ENV_KEY)
        )
    return Path(p)


def _get_test_property(prop: str) -> str:
    global _CONFIG
    if not _CONFIG:
        test_cfg = _get_test_config_file_path()
        config = configparser.ConfigParser()
        config.read(test_cfg)
        if TEST_CONFIG_FILE_SECTION not in config:
            raise TestException(
                "No section {} found in test config file {}".format(
                    TEST_CONFIG_FILE_SECTION, test_cfg
                )
            )
        sec = config[TEST_CONFIG_FILE_SECTION]
        # a section is not a real map and is missing methods
        _CONFIG = {x: sec[x] for x in sec.keys()}
    if prop not in _CONFIG:
        raise TestException(
            "Property {} in section {} of test file {} is missing".format(
                prop, TEST_CONFIG_FILE_SECTION, test_cfg
            )
        )
    return _CONFIG[prop]


def find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def assert_exception_correct(got: Exception, expected: Exception):
    assert type(got) == type(expected)
    assert got.args == expected.args


def assert_ms_epoch_close_to_now(time_):
    now_ms = time.time() * 1000
    assert now_ms + 1000 > time_
    assert now_ms - 1000 < time_


CALLID_PATTERN = re.compile("^\d{16}$")


def assert_json_error_correct(got, expected):
    time_ = got["error"]["time"]
    callid = got["error"]["callid"]
    del got["error"]["time"]
    del got["error"]["callid"]

    assert got == expected
    assert CALLID_PATTERN.match(callid) is not None

    assert_ms_epoch_close_to_now(time_)


class TerstFermerttr(Formatter):

    logs: List[LogRecord] = []

    def __init__(self):
        pass

    def format(self, record):
        self.logs.append(record)
        return "no logs here, no sir"


class TestException(Exception):
    __test__ = False
