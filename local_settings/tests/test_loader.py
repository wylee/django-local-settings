import os
import unittest

from ..loader import Loader
from ..types import LocalSetting


LOCAL_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'local.cfg#test')
DERIVED_LOCAL_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'local.derived.cfg')


class TestLoading(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.loader = Loader(LOCAL_SETTINGS_FILE)

    def test_loading(self):
        local_setting = LocalSetting('default value')
        self.assertEqual(local_setting.default, 'default value')
        self.assertEqual(local_setting.value, 'default value')

        settings = self.loader.load({
            'LOCAL_SETTING': local_setting,
        })

        expected = {
            'LOCAL_SETTING': 'local value',

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

            'STUFF': ['thing', 'another thing'],

            'BASE': {
                'setting': 1,
                'another_setting': 2,
            },

            'OS': {
                'PATH': os.path,
            },

            'FORMAT_STRING': '1{format}'
        }
        self.assertEqual(local_setting.default, 'default value')
        self.assertEqual(local_setting.value, 'local value')
        self.assertEqual(settings.INTERPOLATED.x, 'value')
        self.assertEqual(settings.get_dotted('INTERPOLATED.x'), 'value')
        self.assertEqual(settings, expected)


class TestLoadingDerivedSettings(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.loader = Loader(DERIVED_LOCAL_SETTINGS_FILE)

    def test_loading_derived_settings(self):
        settings = self.loader.load({})
        self.assertEqual(settings.BASE.setting, 1)  # not overridden
        self.assertEqual(settings.BASE.another_setting, "overridden")  # not overridden
