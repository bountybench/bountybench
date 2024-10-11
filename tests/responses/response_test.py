import unittest
from responses.response import Response

class TestResponse(unittest.TestCase):

    def test_parse_field_single_line(self):
        """
        Test that parse_field correctly extracts a single line field.
        """
        text = "command: ls\nanswer: this is an answer"
        result = Response.parse_field(text, "command: ")
        self.assertEqual(result, "ls")

    def test_parse_field_multiline(self):
        """
        Test that parse_field correctly extracts a multiline field.
        """
        text = "description: This is a long description\nthat spans multiple lines.\nEnd here."
        result = Response.parse_field(text, "description: ", multiline=True, stop_str="End here.")
        self.assertEqual(result, "This is a long description\nthat spans multiple lines.")

    def test_parse_field_with_stop_str(self):
        """
        Test that parse_field extracts text and stops at stop_str.
        """
        text = "details: Some text here\nStop after this.\nMore text."
        result = Response.parse_field(text, "details: ", stop_str="Stop after this.")
        self.assertEqual(result, "Some text here")

    def test_parse_field_field_not_found(self):
        """
        Test that parse_field returns None when the field is not found.
        """
        text = "command: ls\nanswer: this is an answer"
        result = Response.parse_field(text, "unknown_field: ")
        self.assertIsNone(result)

    def test_parse_field_no_stop_str(self):
        """
        Test that parse_field extracts until the end of the text if no stop_str is provided.
        """
        text = "note: This is a note.\nIt keeps going until the end."
        result = Response.parse_field(text, "note: ", multiline=True)
        self.assertEqual(result, "This is a note.\nIt keeps going until the end.")

    def test_parse_field_with_case_insensitivity(self):
        """
        Test that parse_field is case-insensitive by default.
        """
        text = "COMMAND: ls\nanswer: this is an answer"
        result = Response.parse_field(text, "command: ")
        self.assertEqual(result, "ls")

    def test_parse_field_no_text_after_field(self):
        """
        Test that parse_field returns None when there's no text after the field.
        """
        text = "command: "
        result = Response.parse_field(text, "command: ")
        self.assertEqual(result, None)

    def test_parse_field_multiline_with_no_stop(self):
        """
        Test that parse_field extracts all lines when no stop_str is provided in multiline mode.
        """
        text = "description: First line\nSecond line\nThird line"
        result = Response.parse_field(text, "description: ", multiline=True)
        self.assertEqual(result, "First line\nSecond line\nThird line")


if __name__ == "__main__":
    unittest.main()
