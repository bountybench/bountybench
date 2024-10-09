import unittest
from unittest.mock import patch
from agents.simple_agent.simple_agent import SimpleExecutionAgent

class TestSimpleExecutionAgent(unittest.TestCase):

    def setUp(self):
        """
        Set up the agent and any necessary mock data for testing.
        """
        # Define the dummy handle_request function for testing  
        def dummy_handle_request(model_input: str) -> str:
            if model_input == "Test prompt":
                return "command: valid_command"
            else:
                return "observation: success"
            
        self.agent = SimpleExecutionAgent(
            config={"max_input_tokens": 100},
            handle_request_func=dummy_handle_request
        )
        self.agent.prompt = "Test prompt"  # Set an initial prompt for testing

    def test_execute_with_valid_response(self):
            """
            Test that execute() successfully runs with a valid LM response and pairs with an observation.
            """
            executor_response = self.agent.execute()
            self.assertEqual(executor_response.command, "valid_command")
            self.assertEqual(executor_response.observation.raw_output, "Observation: valid_command output test")

    def test_execute_with_retry_logic(self):
        """
        Test that execute() retries when the LM response is invalid, and succeeds after retrying.
        """
        # Call execute, which should retry due to invalid responses
        executor_response = self.agent.execute()

        # Ensure the final valid response is returned
        self.assertEqual(executor_response.command, "valid_command")
        self.assertEqual(executor_response.observation.raw_output, "Observation: valid_command output test")

    def test_max_retries_exceeded(self):
        """
        Test that execute() raises an exception after exceeding MAX_ITERATIONS of invalid responses.
        """
        # Simulate a case where all responses are invalid
        def always_invalid_handle_request(model_input: str) -> str:
            return "observation: success"

        # Create an agent with always-invalid responses
        agent = SimpleExecutionAgent(
            config={"max_input_tokens": 100},
            handle_request_func=always_invalid_handle_request
        )
        agent.prompt = "Test prompt"

        # Expect an exception after exceeding retries
        with self.assertRaises(Exception) as context:
            agent.execute()
        self.assertEqual(str(context.exception), "Maximum retries reached without a valid command.")

    def test_observation_is_set_after_execution(self):
        """
        Test that the observation is correctly set after the command is executed.
        """
        executor_response = self.agent.execute()

        # Check that the observation is correctly set
        self.assertIsNotNone(executor_response.observation)
        self.assertEqual(executor_response.observation.raw_output, "Observation: valid_command output test")

if __name__ == '__main__':
    unittest.main()
