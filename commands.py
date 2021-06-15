from runcommands import command
from runcommands.commands import local as _local


@command
def format_code(check=False):
    _local(f"black . {'--check' if check else ''}")


@command
def lint():
    _local("flake8 .")


@command
def test(with_coverage=True, check=True):
    if with_coverage:
        _local(
            "coverage run "
            "--source src/local_settings "
            "-m unittest discover "
            "-t . -s tests "
            "&& coverage report"
        )
    else:
        _local("python -m unittest discover -t . -s tests")
    if check:
        format_code(check=True)
        lint()


@command
def tox(clean=False):
    _local(f"tox {'-r' if clean else ''}")
