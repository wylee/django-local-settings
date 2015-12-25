import unittest

from ..exc import NoDefaultError
from ..types import LocalSetting


class TestLocalSetting(unittest.TestCase):

    def test_create_local_setting(self):
        setting = LocalSetting()
        self.assertRaises(NoDefaultError, lambda: setting.default)
        self.assertFalse(setting.has_default)
        self.assertFalse(setting.has_value)

    def test_create_local_setting_with_default(self):
        setting = LocalSetting(default={})
        self.assertTrue(setting.has_default)
        self.assertEqual(setting.default, {})
        self.assertTrue(setting.has_value)
        self.assertEqual(setting.value, {})

    def test_set_value_of_local_setting_with_default(self):
        setting = LocalSetting(default={})
        setting.value = 'X'
        self.assertEqual(setting.default, {})
        self.assertEqual(setting.value, 'X')

    def test_local_setting_default_must_be_json_serializable(self):
        self.assertRaises(TypeError, LocalSetting, default=object())

    def test_local_setting_can_has_local_setting_as_default(self):
        default_setting = LocalSetting(default=1)
        setting = LocalSetting(default=default_setting)
        self.assertTrue(setting.has_default)
        self.assertEqual(setting.default, 1)
        self.assertEqual(setting.value, 1)
        setting.value = 2
        self.assertEqual(default_setting.value, 1)
        self.assertEqual(setting.value, 2)

    def test_local_setting_with_validator(self):
        setting = LocalSetting(validator=lambda v: isinstance(v, int))
        with self.assertRaises(ValueError):
            setting.value = 'abc'
        setting.value = 123

    def test_local_setting_with_callable_default(self):
        setting = LocalSetting(default=lambda: 'pants')
        self.assertEqual(setting.default, 'pants')
