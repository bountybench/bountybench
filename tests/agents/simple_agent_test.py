import unittest
from unittest.mock import patch, Mock, ANY
from agents.simple_agent.simple_agent import SimpleExecutorAgent    
from responses.command_response import CommandResponse
from responses.answer_response import AnswerResponse
from responses.observation import Observation   
from agents.dataclasses.agent_spec import AgentConfig
from resources.kali_env_resource import KaliEnvResource

# Declare global counter to allow for unique resource names
counter = 0

# Initialize KaliEnvResource for the testing instance
kali_env = KaliEnvResource(name=f"kali-env", volumes=None)

class TestSimpleExecutorAgent(unittest.TestCase):
    def setUp(self):
        global counter
        # Create a mock config for the agent
        self.config = AgentConfig(
            model="openai/o1-mini-2024-09-12",
            max_output_tokens=50,
            max_input_tokens=100,
            max_iterations=3,
            max_response_len=3,
            use_helm=True
        )

        # Initialize the agent
        self.agent = SimpleExecutorAgent(config=self.config)

    def test_run_with_invalid_response_type(self):
        """
        Test run() raises exception when response not valid type
        """
        response = Mock(spec=AnswerResponse)
        with self.assertRaises(Exception) as context:
            self.agent.run(responses=[response])
        self.assertIn('Response not of an interpretable type', str(context.exception))

    def test_run_with_valid_response_type(self):
        """
        Test run() returns valid response
        """
        command_response = CommandResponse("command: ls")
        self.agent.execute = Mock()

        result = self.agent.run(responses=[command_response])

        # Check if execute() was called
        self.agent.execute.assert_called_once()

    def test_execute_calls_lm_and_runs_command(self):
        """
        Tests that execute() calls the LM and executes command.
        """
        # Simulate the call to _handle_request
        self.agent._handle_request = Mock(return_value="command: pwd")

        result = self.agent.execute()

        self.assertEqual(result.observation.raw_output, "Command succeeded: /app\n")

    def test_call_lm_with_command_response(self):
        """
        Test that call_lm correctly returns a CommandResponse.
        """
         # Simulate the call to _handle_request
        self.agent._handle_request = Mock(return_value="command: ls")

        result = self.agent.call_lm()

        # Ensure that the result is a CommandResponse
        self.assertIsInstance(result, CommandResponse)
        self.assertEqual(result.command, "ls")

    def test_call_lm_with_answer_response(self):
        """
        Test that call_lm correctly returns an AnswerResponse.
        """
        # Simulate the call to _handle_request
        self.agent._handle_request = Mock(return_value="answer: 42")

        result = self.agent.call_lm()

        # Ensure that the result is an AnswerResponse
        self.assertIsInstance(result, AnswerResponse)
        self.assertEqual(result.answer, "42")

    def test_execute_in_env_success(self):
        """
        Test that execute_in_env runs the command successfully and returns an Observation.
        """
        response = CommandResponse("command: whoami")
        observation = self.agent.execute_in_env(response)

        self.assertEqual(observation.raw_output, "Command succeeded: root\n")

    def test_execute_in_env_failure(self):
        """
        Test that exeucte_in_env handles command failure correctly.
        """
        response = CommandResponse("command: invalid_command")
        observation = self.agent.execute_in_env(response)

        self.assertIn("Command failed with error", observation.raw_output)

    def test_execute_in_env_timeout(self):
        """
        Test that execute_in_env handles timeout correctly.
        """
        # Simulate timeout
        self.agent._handle_request = Mock(return_value="answer: 42")
        self.agent.kali_env.run_command = Mock(return_value="Command timed out")

        response = CommandResponse("command: sleep 10")
        observation = self.agent.execute_in_env(response)

        self.assertIn("Command execution failed", observation.raw_output)

if __name__ == "__main__":
    unittest.main()
