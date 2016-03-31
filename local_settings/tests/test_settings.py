import doctest
import unittest

from .. import settings
from ..settings import Settings


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(settings))
    return tests


class TestPathParsing(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.settings = Settings()

    def test_simple_path(self):
        segments = self.settings._parse_path('XYZ')
        self.assertEqual(segments, ['XYZ'])

    def test_dotted_path(self):
        segments = self.settings._parse_path('XYZ.abc')
        self.assertEqual(segments, ['XYZ', 'abc'])

    def test_multi_dotted_path(self):
        segments = self.settings._parse_path('XYZ.abc.x.y.z')
        self.assertEqual(segments, ['XYZ', 'abc', 'x', 'y', 'z'])

    def test_compound_path_at_end(self):
        segments = self.settings._parse_path('XYZ.(a.b.c)')
        self.assertEqual(segments, ['XYZ', 'a.b.c'])

    def test_compound_path_in_middle(self):
        segments = self.settings._parse_path('XYZ.(a.b.c).d')
        self.assertEqual(segments, ['XYZ', 'a.b.c', 'd'])

    def test_non_dotted_compound_path(self):
        segments = self.settings._parse_path('XYZ.(abc)')
        self.assertEqual(segments, ['XYZ', 'abc'])

    def test_multi_non_dotted_compound_path_at_end(self):
        segments = self.settings._parse_path('XYZ.(a).(b).(c)')
        self.assertEqual(segments, ['XYZ', 'a', 'b', 'c'])

    def test_multi_non_dotted_compound_path_in_middle(self):
        segments = self.settings._parse_path('XYZ.(a).(b).(c).dddd')
        self.assertEqual(segments, ['XYZ', 'a', 'b', 'c', 'dddd'])

    def test_complex_path(self):
        segments = self.settings._parse_path('XYZ.(a).(b.b).c.(d)')
        self.assertEqual(segments, ['XYZ', 'a', 'b.b', 'c', 'd'])


class TestSetItem(unittest.TestCase):

    def setUp(self):
        self.settings = Settings()

    def test_setitem(self):
        self.settings['a'] = 1
        self.assertIn('a', self.settings)
        self.assertEqual(self.settings['a'], 1)

    def test_setitem_via_dotted_name(self):
        self.settings['a.b'] = 1
        self.assertIn('a', self.settings)
        self.assertIn('b', self.settings['a'])
        self.assertEqual(self.settings['a']['b'], 1)

    def test_setattr(self):
        self.settings.a = Settings()
        self.settings.a.b = 1
        self.assertIn('a', self.settings)
        self.assertIn('b', self.settings['a'])
        self.assertEqual(self.settings['a']['b'], 1)

    def test_setattr_via_dotted_name(self):
        setattr(self.settings, 'a.b', 1)
        self.assertIn('a', self.settings)
        self.assertIn('b', self.settings['a'])
        self.assertEqual(self.settings['a']['b'], 1)


class TestGetItem(unittest.TestCase):

    def setUp(self):
        self.settings = Settings()
        self.settings['a.b.c'] = 'c'

    def test_getitem(self):
        self.assertEqual(self.settings['a']['b']['c'], 'c')

    def test_getitem_via_dotted_name(self):
        self.assertEqual(self.settings['a.b.c'], 'c')

    def test_getattr(self):
        self.assertEqual(self.settings.a.b.c, 'c')

    def test_get_missing(self):
        self.assertRaises(KeyError, self.settings.__getitem__, ('xxx',))

    def test_get_missing_dotted(self):
        self.assertRaises(KeyError, self.settings.__getitem__, ('x.y.z',))


class TestNested(unittest.TestCase):

    def setUp(self):
        self.settings = Settings()

    def test_nested_parentheses(self):
        self.settings['(x(y))'] = 'x'
        keys = list(self.settings.keys())
        self.assertIn('x(y)', keys)
        self.assertEqual(self.settings['(x(y))'], 'x')

    def test_nested_parentheses_with_dots(self):
        self.settings['(x.(y.z))'] = 'x'
        keys = list(self.settings.keys())
        self.assertIn('(x.(y.z))', keys)
        self.assertEqual(self.settings['(x.(y.z))'], 'x')

    def test_nested_empty_parentheses(self):
        self.settings['(())'] = 'x'
        keys = list(self.settings.keys())
        self.assertIn('()', keys)
        self.assertEqual(self.settings['(())'], 'x')

    def test_nested_brackets_with_dots(self):
        self.settings['{x{y}}'] = 'x'
        keys = list(self.settings.keys())
        self.assertIn('{x{y}}', keys)
        self.assertEqual(self.settings['{x{y}}'], 'x')

    def test_nested_brackets_with_dots(self):
        self.settings['{x.{y.z}}'] = 'x'
        keys = list(self.settings.keys())
        self.assertIn('{x.{y.z}}', keys)
        self.assertEqual(self.settings['{x.{y.z}}'], 'x')

    def test_nested_empty_brackets(self):
        self.settings['{{}}'] = 'x'
        keys = list(self.settings.keys())
        self.assertIn('{{}}', keys)
        self.assertEqual(self.settings['{{}}'], 'x')
