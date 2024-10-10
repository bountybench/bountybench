import unittest
from responses.simple_executor_response import SimpleExecutorResponse
from responses.command_response_interface import CommandResponseInterface
from responses.executor_response_interface import ExecutorResponseInterface
from responses.observation import Observation

class TestSimpleExecutorResponse(unittest.TestCase):
    def test_ser_with_command_inherits_from_eri(self):
        ser = SimpleExecutorResponse("command: ls")
        self.assertTrue(issubclass(ser.__class__, ExecutorResponseInterface))  # Should be True

    def test_ser_with_command_inherits_from_cri(self):
        ser = SimpleExecutorResponse("command: ls")
        self.assertTrue(issubclass(ser.__class__, CommandResponseInterface))  # Should be True
        self.assertEqual(ser.command, "ls")  # Ensure command is set correctly

    def test_ser_with_optional_answer(self):
        ser = SimpleExecutorResponse("command: ls\nanswer: this is an answer")
        self.assertEqual(ser.command, "ls")
        self.assertEqual(ser.answer, "this is an answer")  # Ensure answer is optional

    def test_ser_invalid_response_raises_exception(self):
        with self.assertRaises(Exception) as context:
            SimpleExecutorResponse("answer: this is an answer")  # Missing command
        self.assertEqual(str(context.exception), "Command is required but was not found in the response.")

    def test_set_observation(self):
        ser = SimpleExecutorResponse("command: ls")
        ser.set_observation(Observation("file1.txt\nfile2.txt"))
        self.assertEqual(ser.observation.raw_output, "file1.txt\nfile2.txt")

if __name__ == '__main__':
    unittest.main()
