import os
import unittest

from local_settings.checker import Checker
from local_settings.loader import Loader
from local_settings.types import LocalSetting


LOCAL_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "local.cfg#test")


class TestChecker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checker = Checker(LOCAL_SETTINGS_FILE)
        cls.loader = Loader(LOCAL_SETTINGS_FILE)

    def test_checker(self):
        local_setting = LocalSetting("default value")
        settings = self.loader.load(
            {
                "LOCAL_SETTING": local_setting,
            }
        )
        self.checker.check(settings)
