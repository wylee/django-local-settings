import doctest

from .. import color_printer


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(color_printer))
    return tests
