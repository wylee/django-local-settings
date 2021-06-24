import doctest
import math
import unittest
from pathlib import Path

import jsonesque.decoder
import jsonesque.scanner

from jsonesque import decode
from jsonesque.exc import (
    ExpectedKey,
    ExpectedValue,
    ExtraneousData,
    UnexpectedToken,
    UnknownToken,
    UnmatchedBracket,
)


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(jsonesque.decoder))
    tests.addTests(doctest.DocTestSuite(jsonesque.scanner))
    return tests


class TestJSONEsqueScanner(unittest.TestCase):
    def decode(self, string, object_converter=None, disable_extras=False):
        return decode(
            string,
            object_converter=object_converter,
            disable_extras=disable_extras,
        )

    def test_empty_string_is_none(self):
        result = self.decode("")
        self.assertIsNone(result)
        result = self.decode(" ")
        self.assertIsNone(result)

    def test_inf(self):
        self.assertEqual(self.decode("inf"), math.inf)
        self.assertEqual(self.decode("+inf"), math.inf)
        self.assertEqual(self.decode("-inf"), -math.inf)

    def test_nan(self):
        self.assertTrue(math.isnan(float("nan")))
        self.assertTrue(math.isnan(self.decode("nan")))
        self.assertTrue(math.isnan(self.decode("+nan")))
        self.assertTrue(math.isnan(self.decode("-nan")))

    def test_empty_object(self):
        self.assertEqual(self.decode("{}"), {})

    def test_decode_multiline_object(self):
        self.assertEqual(self.decode("{\n\n\n}"), {})

    def test_empty_array(self):
        self.assertEqual(self.decode("[]"), [])

    def test_decode_multiline_array(self):
        self.assertEqual(self.decode("[\n\n\n]"), [])

    def test_simple_object(self):
        self.assertEqual(self.decode('{"a": 1}'), {"a": 1})

    def test_object_with_space_before_key(self):
        self.assertEqual(self.decode('{ "a": 1}'), {"a": 1})

    def test_unclosed_object(self):
        self.assertRaises(UnmatchedBracket, self.decode, '{"a": 1')
        self.assertRaises(ExtraneousData, self.decode, '"a": 1}')

    def test_unclosed_array(self):
        self.assertRaises(UnmatchedBracket, self.decode, "[1, 2")
        self.assertRaises(ExtraneousData, self.decode, "1, 2]")

    def test_nesting(self):
        result = self.decode('{ "1": 0b1, "2": [[1, 2]], }')
        self.assertEqual(result, {"1": 1, "2": [[1, 2]]})

    def test_comments(self):
        self.decode(
            """
            // This is a JSON object
            {
                // "a" is really special
                "a": 1,
                "b": 2,  // end-of-line comment
            }
            """
        )
        self.assertEqual(self.decode('"//"'), "//")
        self.assertEqual(self.decode("//{}"), None)
        self.assertRaises(ExpectedKey, self.decode, "{//}")
        self.assertRaises(ExpectedValue, self.decode, '{"a": //}')
        self.assertRaises(UnmatchedBracket, self.decode, '{"a": 1//}')

    def test_comments_with_extra_features_disabled(self):
        doc = """
        // Comment
        {
            // Comment
            "a": 1,
            "b": 2,
        }
        """
        self.assertRaises(UnknownToken, self.decode, doc, disable_extras=True)

    def test_trailing_commas_with_extra_features_disabled(self):
        self.assertRaises(UnexpectedToken, self.decode, "[1, 2,]", disable_extras=True)


class TestJSONEsqueAgainstJSONCheckerFiles(unittest.TestCase):
    def read(self, name):
        file_name = f"{name}.json"
        path = Path(__file__).parent / "json_checker_files" / file_name
        with path.open() as fp:
            doc = fp.read()
        return doc

    def test_pass1_with_extra_features_disabled(self):
        # Standard JSON shouldn't require any extra features.
        doc = self.read("pass1")
        decode(doc, disable_extras=True)

    def test_pass1_with_extra_features_enabled(self):
        # JSONEsque's extra features are a superset of the standard
        # features, so there shouldn't be any issues parsing a standard
        # JSON doc with them turned on.
        doc = self.read("pass1")
        decode(doc)
