import unittest
from resources.utils import run_command
from responses.command_response import CommandResponse
from responses.command_response_interface import CommandResponseInterface
from responses.answer_response import AnswerResponse
from responses.answer_response_interface import AnswerResponseInterface
from responses.observation import Observation
from responses.response import Response

class TestResponseClasses(unittest.TestCase):

    # def test_command_response_is_response(self):
    #     """
    #     Ensure CommandResponse is a subclass of Response.
    #     """
    #     response = CommandResponse("Command: ls")
    #     self.assertIsInstance(response, Response)

    # def test_answer_response_is_response(self):
    #     """
    #     Ensure AnswerResponse is a subclass of Response.
    #     """
    #     response = AnswerResponse("Answer: 42")
    #     self.assertIsInstance(response, Response)

    # def test_responses_are_not_incorrect_interfaces(self):
    #     # Ensure that the base Response class is not a CommandResponseInterface.
    #     response = Response()
    #     self.assertFalse(isinstance(response, CommandResponseInterface))
    #     # Ensure that CommandResponse is an instance of CommandResponseInterface.
    #     command_response = CommandResponse("Command: ls")
    #     self.assertTrue(isinstance(command_response, CommandResponseInterface))

    # def test_command_response_is_not_answer_response_interface(self):
    #     """
    #     Ensure that CommandResponse is not an instance of AnswerResponseInterface.
    #     """
    #     command_response = CommandResponse("Command: ls")
    #     self.assertFalse(isinstance(command_response, AnswerResponseInterface))

    # def test_answer_response_is_answer_response_interface(self):
    #     """
    #     Ensure that AnswerResponse is an instance of AnswerResponseInterface.
    #     """
    #     answer_response = AnswerResponse("Answer: 42")
    #     self.assertTrue(isinstance(answer_response, AnswerResponseInterface))

    # def test_command_response_parses_command(self):
    #     """
    #     Test that CommandResponse correctly parses the command field.
    #     """
    #     response = CommandResponse("Command: ls")
    #     self.assertEqual(response.command, "ls")

    # def test_answer_response_parses_answer(self):
    #     """
    #     Test that AnswerResponse correctly parses the answer field.
    #     """
    #     response = AnswerResponse("Answer: 42")
    #     self.assertEqual(response.answer, "42")

    # def test_command_response_missing_command_raises_exception(self):
    #     """
    #     Ensure an exception is raised if 'Command' is missing from CommandResponse.
    #     """
    #     with self.assertRaises(Exception) as context:
    #         CommandResponse("Answer: 42")
    #     self.assertEqual(str(context.exception), "Command is missing from response, cannot be a command response.")

    # def test_answer_response_missing_answer_raises_exception(self):
    #     """
    #     Ensure an exception is raised if 'answer' is missing from AnswerResponse.
    #     """
    #     with self.assertRaises(Exception) as context:
    #         AnswerResponse("Command: ls")
    #     self.assertEqual(str(context.exception), "Answer is missing from response, cannot be a answer response.")

    # def test_command_response_set_observation(self):
    #     """
    #     Ensure CommandResponse correctly sets and retrieves an observation.
    #     """
    #     response = CommandResponse("Command: ls")
    #     response.set_observation(Observation("Output of ls command"))
    #     self.assertEqual(response.observation.raw_output, "Output of ls command")

    # def test_command_response_observation_not_set_raises_exception(self):
    #     """
    #     Ensure an exception is raised if observation is accessed before being set in CommandResponse.
    #     """
    #     response = CommandResponse("Command: ls")
    #     with self.assertRaises(Exception) as context:
    #         response.observation
    #     self.assertEqual(str(context.exception), "Observation is missing or the command has not been executed yet.")

    def test_command_response_parsing_prompt_example(self):
        lm_response_str = "Command:\ncat << EOF >> print_file.py\nprint('example of creating a file in python')\nEOF"
        response = CommandResponse(lm_response_str)
        result = run_command(command=response.command)

if __name__ == "__main__":
    unittest.main()