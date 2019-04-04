import os
import unittest

from ..loader import Loader
from ..types import LocalSetting


LOCAL_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'local.cfg#test')
DERIVED_LOCAL_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'local.derived.cfg')


class TestLoading(unittest.TestCase):

    def setUp(self):
        self.loader = Loader(LOCAL_SETTINGS_FILE)

    def test_loading(self):
        local_setting = LocalSetting('default value')
        self.assertEqual(local_setting.default, 'default value')
        self.assertEqual(local_setting.value, 'default value')

        settings = self.loader.load({
            'BASE_SETTING': '{{ PACKAGE }}',
            'LOCAL_SETTING': local_setting,
            'TUPLE_SETTING': ('a', 'b', 'c'),
            'LIST_SETTING': ['a', 'b', 'c'],
            'DICT_SETTING': {'a': 'b'},
            'NESTED_SETTING': {
                'list': ['a', 'b'],
                'tuple': ('a', 'b'),
                'dict': {
                    'list': [1, 2],
                    'tuple': (1, 2),
                }
            }
        })

        expected = {
            'BASE_SETTING': 'local_settings',
            'LOCAL_SETTING': 'local value',
            'TUPLE_SETTING': ('a', 'b', 'c'),
            'LIST_SETTING': ['a', 'b', 'c'],
            'DICT_SETTING': {'a': 'b'},
            'NESTED_SETTING': {
                'list': ['a', 'b'],
                'tuple': ('a', 'b'),
                'dict': {
                    'list': [1, 2],
                    'tuple': (1, 2),
                }
            },

            'PACKAGE': 'local_settings',

            'A': {
                'b': {
                    'c': 1,
                    'd': 2,
                },
            },

            'X': {
                'y': {
                    'z': 'z',
                },
            },

            'LIST': ['a', 'b'],
            'OTHER_LIST': ['a', 'b'],

            'TEMPLATES': [
                {
                    'BACKEND': 'package.module.Class',
                    'OPTIONS': {
                        'context_processors': ['a.b', 'x.y.z'],
                    },
                },
            ],

            'INTERPOLATED': {
                'x': 'value',
                'y': 'value',
                'z': 'value',
            },

            'value': 'interpolated key',
            'I': {
                'value': 'interpolated key',
            },
            'Z': [{'value': 1}],
            'J': {
                'local_settings': {
                    'K': 1,
                },
                'local_settingsXXX': {
                    'L': 2,
                },
            },

            'STUFF': ['a prepended thing', 'thing', 'another thing'],

            'DEFAULT_ITEMS': ['0', 'b', 'c'],

            'BASE': {
                'setting': 1,
                'another_setting': 2,
            },

            'OS': {
                'PATH': os.path,
            },

            'FORMAT_STRING': '1{format}',

            'NUMBER': 1,
            'OTHER_NUMBER': 1,

            'LIST1': [1, 2],
            'LIST2': [1, 2],
            'LIST3': [1, 2],

            'DICT': {'1': 1, '2': [[1, 2]]},
            'OTHER_DICT': {'1': 1, '2': [[1, 2]]},

            'NESTED': {'b': 1.1},
        }

        self.assertEqual(local_setting.default, 'default value')
        self.assertEqual(local_setting.value, 'local value')
        self.assertEqual(settings.INTERPOLATED.x, 'value')
        self.assertEqual(settings.get_dotted('INTERPOLATED.x'), 'value')
        self.assertEqual(settings.DEFAULT_ITEMS, expected['DEFAULT_ITEMS'])

        def check_item(k):
            self.assertIn(k, settings)
            self.assertEqual(settings[k], expected[k])

        if hasattr(self, 'subTest'):  # Python 3.4+
            for key in expected:
                with self.subTest(key=key):
                    check_item(key)
        else:
            for key in expected:
                check_item(key)

    def test_delete(self):
        settings = self.loader.load({})
        self.assertIn('LOCAL_SETTING', settings)

        self.assertIn('A', settings)
        self.assertIn('b', settings.A)
        self.assertIn('c', settings.A.b)
        self.assertIn('d', settings.A.b)

        self.assertIn('LIST1', settings)
        self.assertEqual(settings.LIST1, [1, 2])

        settings = self.loader.load({
            'DELETE': [
                'LOCAL_SETTING',

                # NOTE: LIST.1 = 'b'
                'A.{{ LIST.1 }}.c',

                'LIST1.0',
            ],
        })

        self.assertNotIn('LOCAL_SETTING', settings)

        self.assertIn('A', settings)
        self.assertIn('b', settings.A)
        self.assertNotIn('c', settings.A.b)
        self.assertIn('d', settings.A.b)

        self.assertEqual(settings.LIST1, [2])


class TestLoadTypes(unittest.TestCase):

    def setUp(self):
        settings_file = os.path.join(os.path.dirname(__file__), 'local.cfg#test:empty')
        self.loader = Loader(settings_file)

    def test_load_list(self):
        settings = self.loader.load({
            'LIST': ['a', 'b'],
        })
        self.assertIsInstance(settings.LIST, list)

    def test_load_2_tuple(self):
        settings = self.loader.load({
            'TUPLE': ('a', 'b'),
        })
        self.assertIsInstance(settings.TUPLE, tuple)
        self.assertEqual(settings.TUPLE, ('a', 'b'))

    def test_load_3_tuple(self):
        settings = self.loader.load({
            'TUPLE': ('a', 'b', 'c'),
        })
        self.assertIsInstance(settings.TUPLE, tuple)
        self.assertEqual(settings.TUPLE, ('a', 'b', 'c'))

    def test_load_nested_tuple(self):
        settings = self.loader.load({
            'DICT': {
                'TUPLE': ('a', 'b', 'c'),
            }
        })
        self.assertIsInstance(settings.DICT.TUPLE, tuple)
        self.assertEqual(settings.DICT.TUPLE, ('a', 'b', 'c'))

    def test_load_other_sequence_type(self):
        MyList = type('MyList', (list,), {})
        settings = self.loader.load({
            'MY_LIST': MyList(('a', 'b', 'c')),
        })
        self.assertIsInstance(settings.MY_LIST, MyList)
        self.assertEqual(settings.MY_LIST, ['a', 'b', 'c'])


class TestLoadingDerivedSettings(unittest.TestCase):

    def test_loading_derived_settings(self):
        loader = Loader(DERIVED_LOCAL_SETTINGS_FILE)
        settings = loader.load({})
        self.assertEqual(settings.DEFAULT_ITEM, "overridden")  # overridden
        self.assertEqual(settings.DEFAULT_ITEMS, ['first', 'b', 'c'])
        self.assertEqual(settings.BASE.setting, 1)  # not overridden
        self.assertEqual(settings.BASE.another_setting, "overridden")  # overridden
        self.assertEqual(settings.HIGHER_PRECEDENCE, 'yes')

    def test_loading_derived_settings_where_section_is_not_present_in_derived_settings_file(self):
        loader = Loader(DERIVED_LOCAL_SETTINGS_FILE + '#test:1')
        settings = loader.load({})
        self.assertEqual(settings.ITEM, "item")
