from runcommands import command, printer
from runcommands.commands import local as _local


@command
def format_code(check=False):
    _local(f"black . {'--check' if check else ''}")


@command
def lint():
    _local("flake8 .")


@command
def test(with_coverage=True, check=True, fail_fast=False):
    if with_coverage:
        printer.hr("Django Local Settings Tests - with coverage")
        _local(
            "coverage run "
            "--source src/local_settings "
            "-m unittest discover "
            "-t . -s tests "
            "&& coverage report"
        )
        printer.hr("JSONish Tests - with coverage")
        _local(
            "coverage run "
            "--source src/jsonish/src "
            "-m unittest discover "
            "-t . -s src/jsonish/tests "
            "&& coverage report"
        )
    else:
        fail_fast = "-f" if fail_fast else ""
        printer.hr("Django Local Settings Tests")
        _local(f"python -m unittest discover -t . -s tests {fail_fast}")
        printer.hr("JSONish Tests")
        _local(f"python -m unittest discover -t . -s src/jsonish/tests {fail_fast}")
    if check:
        format_code(check=True)
        lint()


@command
def tox(clean=False):
    _local(f"tox {'-r' if clean else ''}")
