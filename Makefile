build-docs:
	-rm -r docs
	-rm -r docsource/internal_apis
	mkdir -p docs
	sphinx-apidoc --separate -o docsource/internal_apis src src/jgikbase/test/*
	sphinx-build docsource/ docs

test:
	flake8 src
	mypy src
	pytest src --cov src/jgikbase/idmapping
	bandit --recursive src --exclude src/jgikbase/test
	