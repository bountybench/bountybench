import unittest
from unittest.mock import patch, Mock, ANY
from agents.simple_agent.simple_agent import SimpleExecutionAgent
from responses.command_response import CommandResponse
from responses.answer_response import AnswerResponse
from responses.response import Response
from agents.dataclasses.agent_spec import AgentConfig

import subprocess

class TestSimpleExecutionAgent(unittest.TestCase):

    def setUp(self):
        # Create a mock config for the agent
        self.config = AgentConfig(
            model="gpt-4",
            max_output_tokens=50,
            max_input_tokens=100,
            max_iterations=3,
            max_response_len=3,
            helm=False
        )
        # Initialize the agent
        self.agent = SimpleExecutionAgent(config=self.config)

        # Mock the _handle_request method to return valid responses
        def mock_handle_request(model_input):
            if "command:" in model_input:
                print("Handle request sees command in " + model_input)
                return "command: ls"  # Simulate valid command response
            else:
                print("Handle request doesn't see command in " + model_input)
                return "answer: 42"  # Simulate valid answer response

        self.agent._handle_request = mock_handle_request

    def test_run_with_invalid_response_type(self):
        """
        Test that run() raises an exception when the response is not a valid type.
        """
        response = Mock(spec=AnswerResponse)  # Pass AnswerResponse which isn't valid here
        with self.assertRaises(Exception) as context:
            self.agent.run(responses=[response])
        self.assertIn('Response not of an interpretable type', str(context.exception))

    def test_formulate_prompt(self):
        """
        Test that formulate_prompt correctly manages memory and appends responses.
        """
        response = CommandResponse("command: ls")
        
        # Test that memory is updated correctly
        self.agent.formulate_prompt(response)
        self.assertIn(response, self.agent.memory)

        # Simulate adding more responses to exceed max memory
        response2 = CommandResponse("command: pwd")
        response3 = CommandResponse("command: whoami")
        response4 = CommandResponse("command: echo hello")
        
        self.agent.formulate_prompt(response2)
        self.agent.formulate_prompt(response3)
        self.agent.formulate_prompt(response4)
        
        # Ensure the memory contains only the last 3 responses
        self.assertEqual(len(self.agent.memory), 3)
        self.assertNotIn(response, self.agent.memory)  # Oldest should be removed
        self.assertIn(response4, self.agent.memory)

    @patch('agents.simple_agent.simple_agent.SimpleExecutionAgent._handle_request')
    def test_call_lm_with_answer_response(self, mock_handle_request):
        """
        Test that call_lm correctly returns an AnswerResponse.
        """
        mock_handle_request.return_value = "answer: 42"
        
        result = self.agent.call_lm()

        self.assertIsInstance(result, AnswerResponse)
        self.assertEqual(result.answer, "42")

    @patch('subprocess.run')
    def test_execute_in_env_success(self, mock_subprocess_run):
        """
        Test that execute_in_env runs the command successfully and returns an Observation.
        """
        # Simulate successful subprocess execution
        mock_subprocess_run.return_value = Mock(stdout=b"Command output", stderr=b"")

        response = CommandResponse("command: ls")
        observation = self.agent.execute_in_env(response)

        # Check that the observation contains the correct output
        self.assertEqual(observation.raw_output, "Command succeeded: Command output")

    @patch('subprocess.run')
    def test_execute_in_env_timeout(self, mock_subprocess_run):
        """
        Test that execute_in_env handles timeouts correctly.
        """
        # Simulate a timeout in subprocess
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired(cmd="ls", timeout=120)

        response = CommandResponse("command: ls")
        observation = self.agent.execute_in_env(response)

        # Check that the observation reports a timeout
        self.assertIn("Command timed out", observation.raw_output)

    @patch('subprocess.run')
    def test_execute_in_env_failure(self, mock_subprocess_run):
        """
        Test that execute_in_env handles command failure correctly.
        """
        # Simulate a command error
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "ls", stderr=b"Command not found")

        response = CommandResponse("command: ls")
        observation = self.agent.execute_in_env(response)

        # Check that the observation reports a command failure
        self.assertIn("Command failed with error: Command not found", observation.raw_output)

    def test_run_and_call_lm_return_response_type(self):
        """
        Ensure both run() and call_lm() return a valid Response type (either CommandResponse or AnswerResponse).
        """
        # Manually set a valid command in the agent's prompt
        self.agent.prompt = "command: ls"

        # Test call_lm directly
        lm_response = self.agent.call_lm()
        self.assertTrue(isinstance(lm_response, Response), "call_lm did not return a Response type.")
        self.assertTrue(isinstance(lm_response, (CommandResponse, AnswerResponse)),
                        "call_lm did not return a CommandResponse or AnswerResponse.")

        # Test run with a command response
        command_response = CommandResponse("command: ls")
        run_response = self.agent.run(responses=[command_response])
        self.assertTrue(isinstance(run_response, Response), "run did not return a Response type.")
        self.assertTrue(isinstance(run_response, (CommandResponse, AnswerResponse)),
                        "run did not return a CommandResponse or AnswerResponse.")


if __name__ == "__main__":
    unittest.main()
