import unittest
from response import parse_field

class TestParseField(unittest.TestCase):
    def test_basic_extraction(self):
        """Test that a field is correctly extracted from the text."""
        text = "command: run_this_script"
        field = "command: "
        expected = "run_this_script"
        self.assertEqual(parse_field(text, field), expected)

    def test_case_insensitivity(self):
        """Test that the extraction works with case insensitivity."""
        text = "COMMAND: run_this_script"
        field = "command: "
        expected = "run_this_script"
        self.assertEqual(parse_field(text, field, case_sensitive=False), expected)

    def test_case_sensitivity(self):
        """Test that case sensitivity works as expected."""
        text = "COMMAND: run_this_script"
        field = "command: "
        expected = ""
        self.assertEqual(parse_field(text, field, case_sensitive=True), expected)

    def test_stop_string(self):
        """Test that extraction stops correctly when stop_str is provided."""
        text = "command: run_this_script; observation: success"
        field = "command: "
        stop_str = ";"
        expected = "run_this_script"
        self.assertEqual(parse_field(text, field, stop_str=stop_str), expected)

    def test_stop_string_not_found(self):
        """Test that when stop_str is not found, it extracts until the end."""
        text = "command: run_this_script observation: success"
        field = "command: "
        stop_str = ";"
        expected = "run_this_script observation: success"
        self.assertEqual(parse_field(text, field, stop_str=stop_str), expected)

    def test_field_not_found(self):
        """Test that an empty string is returned if the field is not found."""
        text = "observation: success"
        field = "command: "
        expected = ""
        self.assertEqual(parse_field(text, field), expected)

    def test_empty_text(self):
        """Test that an empty string is returned if the input text is empty."""
        text = ""
        field = "command: "
        expected = ""
        self.assertEqual(parse_field(text, field), expected)

    def test_no_stop_str(self):
        """Test that it extracts until the end if no stop_str is provided."""
        text = "command: run_this_script observation: success"
        field = "command: "
        expected = "run_this_script observation: success"
        self.assertEqual(parse_field(text, field), expected)

if __name__ == '__main__':
    unittest.main()
