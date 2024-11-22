import json
import os
import pytest
import requests
import time


""" id_mapping_service_container_test.py

Very simple tests to ensure that local id mapping server is functioning correctly.
Requires the python libraries `pytest` and `requests` to be installed.

Assumes that the id mapping service is running locally on ports 8080.

Use the wrapper shell script, `run_tests.sh`, to create the necessary set up and run the tests:

sh container_test/run_tests.sh

"""

SERVICE = "ID Mapping Service"
ID_MAPPING_SERVICE_VERSION = "0.1.2"

ID_MAPPING_URL = "http://localhost:8080"
WAIT_TIMES = [1, 2, 5, 10, 30]

NAMESPACE_1 = "sijie"
NAMESPACE_2 = "gavin"


@pytest.fixture(scope="module")
def ready():
    wait_for_id_mapping_service()

    yield


def wait_for_id_mapping_service():
    print("waiting for id mapping service...")

    attempt = 1
    max_attempts = len(WAIT_TIMES) + 1
    while attempt <= max_attempts:
        print(f"Attempt {attempt} of {max_attempts}")
        try:
            res = requests.get(ID_MAPPING_URL)
            res.raise_for_status()
            return
        except Exception as e:
            if attempt < max_attempts:
                t = WAIT_TIMES[attempt - 1]
                print(
                    f"Failed to connect to id mapping service, waiting {t} sec "
                    f"and trying again:\n\t{e}"
                )
                time.sleep(t)
            attempt += 1
    raise Exception(
        f"Couldn't connect to the id mapping service after {max_attempts} attempts"
    )


def test_id_mapping_service(ready) -> None:
    """create two namespaces, add admins, create mappings, and list mappings"""
    user, token = get_user_and_token()
    test_id_mapping_version()
    create_namespaces(token)
    add_admins(user, token)
    create_mappings(token)
    list_mappings()


def create_namespaces(token) -> None:
    response_1 = requests.put(
        ID_MAPPING_URL + f"/api/v1/namespace/{NAMESPACE_1}",
        headers={"authorization": f"local {token}"},
    )

    response_2 = requests.put(
        ID_MAPPING_URL + f"/api/v1/namespace/{NAMESPACE_2}",
        headers={"authorization": f"local {token}"},
    )

    assert response_1.status_code == 204
    assert response_2.status_code == 204


def add_admins(user: str, token: str) -> None:
    response_1 = requests.put(
        ID_MAPPING_URL + f"/api/v1/namespace/{NAMESPACE_1}/user/local/{user}",
        headers={"authorization": f"local {token}"},
    )

    response_2 = requests.put(
        ID_MAPPING_URL + f"/api/v1/namespace/{NAMESPACE_2}/user/local/{user}",
        headers={"authorization": f"local {token}"},
    )

    assert response_1.status_code == 204
    assert response_2.status_code == 204


def create_mappings(token: str) -> None:
    response = requests.put(
        ID_MAPPING_URL + f"/api/v1/mapping/{NAMESPACE_1}/{NAMESPACE_2}",
        headers={"Authorization": "local " + token},
        json={"id1": "id2", "id3": "id4", "id5": "id6"},
    )

    assert response.status_code == 204


def list_mappings() -> None:
    response = requests.get(
        ID_MAPPING_URL + f"/api/v1/mapping/{NAMESPACE_2}?separate",
        data=json.dumps({"ids": ["id2", "id4", "id8"]}),
    )

    assert response.status_code == 200
    assert response.json() == {
        "id2": {"admin": [], "other": [{"id": "id1", "ns": NAMESPACE_1}]},
        "id4": {"admin": [], "other": [{"id": "id3", "ns": NAMESPACE_1}]},
        "id8": {"admin": [], "other": []},
    }


def test_id_mapping_version() -> None:
    """get the current id mapping service version"""
    res = requests.get(ID_MAPPING_URL)
    assert res.status_code == 200
    data = res.json()
    assert data["service"] == SERVICE
    assert data["version"] == ID_MAPPING_SERVICE_VERSION


def get_user_and_token() -> tuple[str, str]:
    user = os.environ["USER"]
    token = os.environ["ID_MAPPER_OUTPUT"].split("\n")[1]
    return user, token
