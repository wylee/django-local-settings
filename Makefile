.PHONY: init test

init:
	virtualenv -p python3 .env
	.env/bin/pip install -e .
	.env/bin/pip install django
	$(MAKE) test

test:
	.env/bin/python -m unittest discover .
