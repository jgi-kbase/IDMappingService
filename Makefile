test:
	flake8 src
	mypy src
	pytest src
	bandit --recursive src --exclude src/jgikbase/test
	