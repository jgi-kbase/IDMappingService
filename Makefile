CWD = $(shell pwd)

TEST_CFG = $(CWD)/test.cfg

build-docs:
	-rm -r docs
	-rm -r docsource/internal_apis
	mkdir -p docs
	sphinx-apidoc --separate -o docsource/internal_apis src src/jgikbase/test/* src/app.py
	sphinx-build docsource/ docs

test:
	flake8 src
	mypy src
	IDMAP_TEST_FILE=$(TEST_CFG) pytest --verbose src --cov src/jgikbase/idmapping
	bandit --recursive src --exclude src/jgikbase/test

# Only test the MongoDB related code.
test-mongo:
	IDMAP_TEST_FILE=$(TEST_CFG) pytest --verbose src/jgikbase/test/idmapping/storage/mongo

docker_image:
	./build/build_docker_image.sh