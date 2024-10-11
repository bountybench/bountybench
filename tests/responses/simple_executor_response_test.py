import unittest
from responses.simple_executor_response import SimpleExecutorResponse
from responses.command_response_interface import CommandResponseInterface
from responses.executor_response_interface import ExecutorResponseInterface
from responses.observation import Observation
from responses.action_response import ActionType

class TestSimpleExecutorResponse(unittest.TestCase):
    def test_ser_with_command_inherits_from_eri(self):
        ser = SimpleExecutorResponse("command: ls")
        self.assertTrue(issubclass(ser.__class__, ExecutorResponseInterface))  # Should be True

    def test_ser_with_command_inherits_from_cri(self):
        ser = SimpleExecutorResponse("command: ls")
        self.assertTrue(issubclass(ser.__class__, CommandResponseInterface))  # Should be True
        self.assertEqual(ser.command, "ls")  # Ensure command is set correctly

    def test_set_observation(self):
        ser = SimpleExecutorResponse("command: ls")
        ser.set_observation(Observation("file1.txt\nfile2.txt"))
        self.assertEqual(ser.observation.raw_output, "file1.txt\nfile2.txt")

    def test_command_response_action(self):
        # Create a SimpleExecutorResponse with a command in the response
        response_str = "command: echo hello"
        executor_response = SimpleExecutorResponse(response_str)

        # Verify action is a command
        self.assertEqual(executor_response.action, ActionType.COMMAND)
        self.assertEqual(executor_response.command, "echo hello")
        self.assertIsNone(executor_response.answer)

    def test_answer_response_action(self):
        # Create a SimpleExecutorResponse with an answer in the response
        response_str = "answer: 42"
        executor_response = SimpleExecutorResponse(response_str)

        # Verify that the action is ANSWER
        self.assertEqual(executor_response.action, ActionType.ANSWER)

        # Verify that the answer is correctly parsed
        self.assertEqual(executor_response.answer, "42")
        
        # Verify that the command is None (since it's an answer response)
        self.assertIsNone(executor_response.command)
        
    def test_missing_action_raises_exception(self):
        # Create a SimpleExecutorResponse without a command or answer
        response_str = "some irrelevant text"

        # Verify that an exception is raised for missing action
        with self.assertRaises(Exception) as context:
            SimpleExecutorResponse(response_str)

        self.assertEqual(str(context.exception), "An action of either command or answer is required but was not found in the response.")


if __name__ == '__main__':
    unittest.main()
