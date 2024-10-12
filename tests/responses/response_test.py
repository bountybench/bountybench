import unittest
from responses.command_response import CommandResponse
from responses.command_response_interface import CommandResponseInterface
from responses.answer_response import AnswerResponse
from responses.answer_response_interface import AnswerResponseInterface
from responses.response import Response

class TestResponseClasses(unittest.TestCase):

    def test_command_response_is_response(self):
        """
        Ensure CommandResponse is a subclass of Response.
        """
        response = CommandResponse("command: ls")
        self.assertIsInstance(response, Response)

    def test_answer_response_is_response(self):
        """
        Ensure AnswerResponse is a subclass of Response.
        """
        response = AnswerResponse("answer: 42")
        self.assertIsInstance(response, Response)

    def test_responses_are_not_incorrect_interfaces(self):
        # Ensure that the base Response class is not a CommandResponseInterface.
        response = Response()
        self.assertFalse(isinstance(response, CommandResponseInterface))
        # Ensure that CommandResponse is an instance of CommandResponseInterface.
        command_response = CommandResponse("command: ls")
        self.assertTrue(isinstance(command_response, CommandResponseInterface))

    def test_command_response_is_not_answer_response_interface(self):
        """
        Ensure that CommandResponse is not an instance of AnswerResponseInterface.
        """
        command_response = CommandResponse("command: ls")
        self.assertFalse(isinstance(command_response, AnswerResponseInterface))

    def test_answer_response_is_answer_response_interface(self):
        """
        Ensure that AnswerResponse is an instance of AnswerResponseInterface.
        """
        answer_response = AnswerResponse("answer: 42")
        self.assertTrue(isinstance(answer_response, AnswerResponseInterface))

    def test_command_response_parses_command(self):
        """
        Test that CommandResponse correctly parses the command field.
        """
        response = CommandResponse("command: ls")
        self.assertEqual(response.command, "ls")

    def test_answer_response_parses_answer(self):
        """
        Test that AnswerResponse correctly parses the answer field.
        """
        response = AnswerResponse("answer: 42")
        self.assertEqual(response.answer, "42")

    def test_command_response_missing_command_raises_exception(self):
        """
        Ensure an exception is raised if 'command' is missing from CommandResponse.
        """
        with self.assertRaises(Exception) as context:
            CommandResponse("answer: 42")
        self.assertEqual(str(context.exception), "Command is missing from response, cannot be a command response.")

    def test_answer_response_missing_answer_raises_exception(self):
        """
        Ensure an exception is raised if 'answer' is missing from AnswerResponse.
        """
        with self.assertRaises(Exception) as context:
            AnswerResponse("command: ls")
        self.assertEqual(str(context.exception), "Answer is missing from response, cannot be a answer response.")

    def test_command_response_set_observation(self):
        """
        Ensure CommandResponse correctly sets and retrieves an observation.
        """
        response = CommandResponse("command: ls")
        response.set_observation("Output of ls command")
        self.assertEqual(response.observation, "Output of ls command")

    def test_command_response_observation_not_set_raises_exception(self):
        """
        Ensure an exception is raised if observation is accessed before being set in CommandResponse.
        """
        response = CommandResponse("command: ls")
        with self.assertRaises(Exception) as context:
            response.observation
        self.assertEqual(str(context.exception), "Observation is missing or the command has not been executed yet.")

if __name__ == "__main__":
    unittest.main()

# import unittest
# from responses.response import Response

# class TestResponse(unittest.TestCase):

#     def test_parse_field_single_line(self):
#         """
#         Test that parse_field correctly extracts a single line field.
#         """
#         text = "command: ls\nanswer: this is an answer"
#         result = Response.parse_field(text, "command: ")
#         self.assertEqual(result, "ls")

#     def test_parse_field_multiline(self):
#         """
#         Test that parse_field correctly extracts a multiline field.
#         """
#         text = "description: This is a long description\nthat spans multiple lines.\nEnd here."
#         result = Response.parse_field(text, "description: ", multiline=True, stop_str="End here.")
#         self.assertEqual(result, "This is a long description\nthat spans multiple lines.")

#     def test_parse_field_with_stop_str(self):
#         """
#         Test that parse_field extracts text and stops at stop_str.
#         """
#         text = "details: Some text here\nStop after this.\nMore text."
#         result = Response.parse_field(text, "details: ", stop_str="Stop after this.")
#         self.assertEqual(result, "Some text here")

#     def test_parse_field_field_not_found(self):
#         """
#         Test that parse_field returns None when the field is not found.
#         """
#         text = "command: ls\nanswer: this is an answer"
#         result = Response.parse_field(text, "unknown_field: ")
#         self.assertIsNone(result)

#     def test_parse_field_no_stop_str(self):
#         """
#         Test that parse_field extracts until the end of the text if no stop_str is provided.
#         """
#         text = "note: This is a note.\nIt keeps going until the end."
#         result = Response.parse_field(text, "note: ", multiline=True)
#         self.assertEqual(result, "This is a note.\nIt keeps going until the end.")

#     def test_parse_field_with_case_insensitivity(self):
#         """
#         Test that parse_field is case-insensitive by default.
#         """
#         text = "COMMAND: ls\nanswer: this is an answer"
#         result = Response.parse_field(text, "command: ")
#         self.assertEqual(result, "ls")

#     def test_parse_field_no_text_after_field(self):
#         """
#         Test that parse_field returns None when there's no text after the field.
#         """
#         text = "command: "
#         result = Response.parse_field(text, "command: ")
#         self.assertEqual(result, None)

#     def test_parse_field_multiline_with_no_stop(self):
#         """
#         Test that parse_field extracts all lines when no stop_str is provided in multiline mode.
#         """
#         text = "description: First line\nSecond line\nThird line"
#         result = Response.parse_field(text, "description: ", multiline=True)
#         self.assertEqual(result, "First line\nSecond line\nThird line")


# if __name__ == "__main__":
#     unittest.main()
