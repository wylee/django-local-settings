import unittest

from local_settings.exc import NoDefaultError
from local_settings.types import EnvSetting


class TestEnvSetting(unittest.TestCase):
    def test_create_env_setting(self):
        setting = EnvSetting("TEST_ENV_SETTING")
        self.assertRaises(NoDefaultError, lambda: setting.default)
        self.assertFalse(setting.has_default)
        self.assertFalse(setting.has_value)

    def test_env_setting_cannot_have_a_default(self):
        self.assertRaises(TypeError, EnvSetting, default="pants")
