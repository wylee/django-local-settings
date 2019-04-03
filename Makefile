distribution = django-local-settings
egg_name = $(distribution:-=_)
egg_info = $(egg_name).egg-info
package = local_settings
sdist = dist/$(distribution)-$(version).tar.gz
venv = .venv
python_version ?= python3
version = $(shell sed -n "s/__version__ = '\(..*\)'/\1/p" local_settings/__init__.py)

sources = $(shell find . \
    \( \
        -name '*.py?' -o \
        -path '*/.*' -o \
        -path '*/__pycache__*' -o \
        -path './*.egg-info*' -o \
        -path './build*' -o \
        -path './dist*' \
    \) \
    -prune -o \
    -type f \
    -print \
)

init: install test
reinit: clean-venv clean-install init

venv: $(venv)
$(venv):
	virtualenv -p $(python_version) $(venv)
clean-venv:
	rm -rf $(venv)

install: venv $(egg_info)
reinstall: clean-install install
$(egg_info):
	$(venv)/bin/pip install -e .[dev]
clean-install:
	rm -rf $(egg_info)

test: install
	$(venv)/bin/python -m unittest discover
coverage:
	$(venv)/bin/coverage run --source $(package) -m unittest discover && coverage report

tox: install
	$(venv)/bin/tox
tox-clean:
	rm -rf .tox
retox: tox-clean tox

sdist: $(sdist)
$(sdist): $(sources)
	$(venv)/bin/pip install -e .[dev]
	python setup.py sdist
clean-sdist:
	rm -f $(sdist)

upload-to-pypi:
	twine upload $(sdist)

clean: clean-pyc
clean-all: clean-install clean-pyc clean-sdist clean-venv
	rm -rf build dist
clean-pyc:
	find . -name __pycache__ -type d -print0 | xargs -0 rm -r
	find . -name '*.py?' -type f -print0 | xargs -0 rm

.PHONY = \
    init reinit venv install reinstall test coverage sdist upload-to-pypi \
    clean-venv clean-install clean-sdist clean clean-all clean-pyc
