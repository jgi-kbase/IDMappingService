test:
	flake8 src
	mypy src
	pytest src --cov src/jgikbase/idmapping
	bandit --recursive src --exclude src/jgikbase/test
	