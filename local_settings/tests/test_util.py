import os
import unittest

from ..util import NO_DEFAULT, get_file_name


class TestUtil(unittest.TestCase):

    def test_NO_DEFAULT_is_False(self):
        self.assertFalse(NO_DEFAULT)

    def test_default_file_name(self):
        os.chdir(os.path.dirname(__file__))
        os.environ.pop('LOCAL_SETTINGS_FILE', None)
        file_name = get_file_name()
        self.assertEqual(os.path.basename(file_name), 'local.cfg')

    def test_set_file_name_via_environ(self):
        os.environ['LOCAL_SETTINGS_FILE'] = 'pants.cfg'
        file_name = get_file_name()
        self.assertEqual(file_name, 'pants.cfg')
