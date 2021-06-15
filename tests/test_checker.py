import os
import unittest

from local_settings.checker import Checker
from local_settings.loader import Loader
from local_settings.types import EnvSetting, LocalSetting


LOCAL_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "local.cfg#test")


class TestChecker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checker = Checker(LOCAL_SETTINGS_FILE)
        cls.loader = Loader(LOCAL_SETTINGS_FILE)

    def test_checker(self):
        os.environ["ENV_SETTING"] = "{{ PACKAGE }}"
        os.environ["NESTED_ENV_SETTING"] = "{{ LOCAL_SETTING }}"
        settings = self.loader.load(
            {
                "LOCAL_SETTING": LocalSetting("default value"),
                "ENV_SETTING": EnvSetting("ENV_SETTING"),
                "NESTED_ENV_SETTING": {
                    "nested": EnvSetting("NESTED_ENV_SETTING"),
                },
            }
        )
        self.checker.check(settings)
        self.assertEqual(settings["LOCAL_SETTING"], "local value")
        self.assertEqual(settings["ENV_SETTING"], "local_settings")
        self.assertEqual(settings["NESTED_ENV_SETTING"]["nested"], "local value")
