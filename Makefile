CWD = $(shell pwd)

TEST_CFG = $(CWD)/test.cfg

build-docs:
	-rm -r docs
	-rm -r docsource/internal_apis
	mkdir -p docs
	sphinx-apidoc --separate -o docsource/internal_apis src src/jgikbase/test/*
	sphinx-build docsource/ docs

test:
	flake8 src
	mypy src
	IDMAP_TEST_FILE=$(TEST_CFG) pytest src --cov src/jgikbase/idmapping
	bandit --recursive src --exclude src/jgikbase/test
	