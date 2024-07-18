#!/usr/bin/env bash
#
# Script to run the python id_mapping_service_container_test.py locally or on GitHub Actions.
# Builds and mounts id mapping service and mongo docker containers, and then calls
# the python script.
#
# See .github/workflows/test.yml for GitHub Actions implementation.

# build and start the containers
docker compose up -d --build
compose_up_exit_code=$?
if [ $compose_up_exit_code -ne 0 ]; then
    echo "Error: docker-compose up -d --build command failed with exit code $compose_up_exit_code."
    exit $compose_up_exit_code
fi

export USER=myname
# create user myname with token
export TOKEN=$(docker exec id_mapper_container /bin/sh ./id_mapper --user $USER --create)
# set user myname's admin state to true
docker exec id_mapper_container /bin/sh ./id_mapper --user $USER --admin true

# get the path to the current directory and add it to the python execution path
current_dir="$( dirname -- "$( readlink -f -- "$0"; )"; )"
PYTHONPATH="$current_dir":$PYTHONPATH python -m pytest container_test/id_mapping_service_container_test.py
exit_code=$?

docker compose down
exit $exit_code