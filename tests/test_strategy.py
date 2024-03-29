import doctest

import local_settings.strategy


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(local_settings.strategy))
    return tests
