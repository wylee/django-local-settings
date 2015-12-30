.PHONY: init test

init:
	test -d .env && rm -rf .env || true
	virtualenv -p python3 .env
	.env/bin/pip install -e .[dev]
	$(MAKE) test

test:
	.env/bin/python -m unittest discover .

coverage:
	.env/bin/coverage run --source local_settings -m unittest discover . && coverage report
