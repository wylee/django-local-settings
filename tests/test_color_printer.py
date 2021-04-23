import doctest

import local_settings.color_printer


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(local_settings.color_printer))
    return tests
