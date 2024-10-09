import unittest
from responses.executor_response import SimpleExecutorResponse
from responses.observation import Observation

class TestExecutorResponse(unittest.TestCase):

    def test_pair_response_and_observation(self):
        response = "command: ls"
        observation = Observation("file1.txt\nfile2.txt\n")
        
        # Create an SimpleExecutorResponse with a response but no observation initially
        executor_response = SimpleExecutorResponse(response)
        self.assertEqual(executor_response.command, "ls")
        
        # Set the observation and ensure it pairs correctly
        executor_response.set_observation(observation)
        self.assertEqual(executor_response.observation.raw_output, "file1.txt\nfile2.txt\n")

if __name__ == '__main__':
    unittest.main()