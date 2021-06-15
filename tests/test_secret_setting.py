import unittest

from local_settings.exc import DefaultValueError
from local_settings.types import SecretSetting


class TestSecretSetting(unittest.TestCase):
    def test_create_secret_setting(self):
        setting = SecretSetting()
        self.assertFalse(setting.has_default)
        self.assertFalse(setting.has_value)

    def test_secret_setting_can_have_a_callable_default(self):
        setting = SecretSetting(default=lambda: "pants")
        self.assertEqual(setting.default, "pants")

    def test_secret_setting_cannot_have_a_simple_default(self):
        self.assertRaises(DefaultValueError, SecretSetting, default="pants")
