import unittest
from agents.simple_agent.simple_agent import SimpleExecutionAgent
from responses.simple_executor_response import SimpleExecutorResponse
from responses.executor_response_interface import ExecutorResponseInterface
from responses.observation import Observation
from unittest.mock import patch
import subprocess

class TestSimpleExecutionAgent(unittest.TestCase):
    def setUp(self):
        """
        Set up the agent and any necessary mock data for testing.
        """
        # Define the dummy handle_request function for testing  
        def dummy_handle_request(model_input: str) -> str:
            if model_input == "Valid prompt":
                return "command: ls"
            else:
                return "invalid response"
            
        self.agent = SimpleExecutionAgent(
            config={"max_input_tokens": 100},
            handle_request_func=dummy_handle_request
        )
        self.agent.prompt = "Valid prompt"  # Set an initial prompt for testing

    def test_execute_with_valid_command_response(self):
        """
        Test that execute() successfully runs with a valid command in the LM response.
        """
        # Ensure that the agent executes and retrieves the correct command
        executor_response = self.agent.execute()
        self.assertEqual(executor_response.command, "ls")
    
    def test_call_lm_retries_invalid_response(self):
        """
        Test that call_lm() retries when the LM response is invalid (missing a command).
        """
        # Modify prompt to trigger invalid response and ensure retries happen
        self.agent.prompt = "Invalid prompt"

        with patch.object(self.agent, "MAX_ITERATIONS", 3):
            with self.assertRaises(Exception) as context:
                self.agent.call_lm()
            self.assertEqual(str(context.exception), "Maximum retries reached without a valid response.")

    def test_execute_with_retry_logic(self):
        """
        Test that execute() retries when the LM response is invalid, and succeeds after retrying.
        """
        retry_counter = {'count': 0}  # To keep track of retries
        
        def retrying_handle_request(model_input: str) -> str:
            # Simulate returning invalid responses for the first two retries, then a valid one
            retry_counter['count'] += 1
            if retry_counter['count'] < 3:  # First two retries are invalid
                return "invalid response"
            else:  # Third response is valid
                return "command: ls"
        
        # Update handle_request_func with retry logic
        self.agent.handle_request_func = retrying_handle_request

        # Call execute, which should retry due to invalid responses and succeed after retry
        executor_response = self.agent.execute()
        
        # Ensure the valid response was processed after retries
        self.assertEqual(executor_response.command, "ls")

    def test_subclass_inheritance_check(self):
        """
        Test that the response classes during execution process maintain correct subclass relations.
        """
        executor_response = self.agent.execute()
        
        # Check that the response is a subclass of ExecutorResponseInterface
        self.assertTrue(issubclass(executor_response.__class__, ExecutorResponseInterface))

        # Check that the response contains the expected command
        self.assertEqual(executor_response.command, "ls")

    def test_execute_in_env_successful(self):
        # Simulate a valid command
        executor_response = SimpleExecutorResponse("command: ls")
        observation = self.agent.execute_in_env(executor_response)

        self.assertIsInstance(observation, Observation)

    def test_execute_in_env_failure(self):
        # Simulate an invalid command
        executor_response = SimpleExecutorResponse("command: invalidcommand")
        observation = self.agent.execute_in_env(executor_response)
        
        self.assertIn("Command failed", observation.raw_output)  # Check for failure observation

    def test_execute_in_env_timeout(self):
        # Simulate a command that takes too long (timeout case)
        executor_response = SimpleExecutorResponse("command: sleep 130")  # Sleep for more than 120 seconds
        observation = self.agent.execute_in_env(executor_response)
        
        self.assertIn("Command timed out", observation.raw_output)  # Check for timeout observation

    @patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd="sleep", timeout=120))
    def test_execute_in_env_timeout(self, mock_run):
        # Simulate a command that takes too long (timeout case)
        executor_response = SimpleExecutorResponse("command: sleep 130")
        observation = self.agent.execute_in_env(executor_response)
        
        self.assertIn("Command timed out", observation.raw_output)

if __name__ == '__main__':
    unittest.main()
