import os
import tempfile
from unittest import TestCase

from .exc import NoDefaultError
from .loader import Loader
from .types import LocalSetting, SecretSetting
from .util import NO_DEFAULT, get_file_name


class TestUtil(TestCase):

    def test_NO_DEFAULT_is_False(self):
        self.assertFalse(NO_DEFAULT)

    def test_default_file_name(self):
        os.environ.pop('LOCAL_SETTINGS_FILE', None)
        file_name = get_file_name()
        self.assertEqual(os.path.basename(file_name), 'local.cfg')

    def test_set_file_name_via_environ(self):
        os.environ['LOCAL_SETTINGS_FILE'] = 'pants.cfg'
        file_name = get_file_name()
        self.assertEqual(file_name, 'pants.cfg')


class TestLocalSetting(TestCase):

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


class TestSecretSetting(TestCase):

    def test_create_secret_setting(self):
        setting = SecretSetting()
        self.assertFalse(setting.has_default)
        self.assertFalse(setting.has_value)

    def test_secret_setting_cannot_have_a_default(self):
        self.assertRaises(TypeError, SecretSetting, default='pants')


class TestPathParsing(TestCase):

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(mode='r')
        self.loader = Loader(self.temp_file.name)

    def tearDown(self):
        self.temp_file.close()

    def test_simple_path(self):
        segments = self.loader._parse_path('XYZ')
        self.assertEqual(segments, ['XYZ'])

    def test_dotted_path(self):
        segments = self.loader._parse_path('XYZ.abc')
        self.assertEqual(segments, ['XYZ', 'abc'])

    def test_multi_dotted_path(self):
        segments = self.loader._parse_path('XYZ.abc.x.y.z')
        self.assertEqual(segments, ['XYZ', 'abc', 'x', 'y', 'z'])

    def test_compound_path_at_end(self):
        segments = self.loader._parse_path('XYZ.(a.b.c)')
        self.assertEqual(segments, ['XYZ', 'a.b.c'])

    def test_compound_path_in_middle(self):
        segments = self.loader._parse_path('XYZ.(a.b.c).d')
        self.assertEqual(segments, ['XYZ', 'a.b.c', 'd'])

    def test_non_dotted_compound_path(self):
        segments = self.loader._parse_path('XYZ.(abc)')
        self.assertEqual(segments, ['XYZ', 'abc'])

    def test_multi_non_dotted_compound_path_at_end(self):
        segments = self.loader._parse_path('XYZ.(a).(b).(c)')
        self.assertEqual(segments, ['XYZ', 'a', 'b', 'c'])

    def test_multi_non_dotted_compound_path_in_middle(self):
        segments = self.loader._parse_path('XYZ.(a).(b).(c).dddd')
        self.assertEqual(segments, ['XYZ', 'a', 'b', 'c', 'dddd'])

    def test_complex_path(self):
        segments = self.loader._parse_path('XYZ.(a).(b.b).c.(d)')
        self.assertEqual(segments, ['XYZ', 'a', 'b.b', 'c', 'd'])
