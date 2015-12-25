import unittest

from ..types import SecretSetting


class TestSecretSetting(unittest.TestCase):

    def test_create_secret_setting(self):
        setting = SecretSetting()
        self.assertFalse(setting.has_default)
        self.assertFalse(setting.has_value)

    def test_secret_setting_cannot_have_a_default(self):
        self.assertRaises(TypeError, SecretSetting, default='pants')
