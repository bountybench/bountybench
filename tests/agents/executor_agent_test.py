import unittest
from unittest.mock import Mock, patch
from agents.executor_agent.executor_agent import ExecutorAgent    
from models.model_response import ModelResponse
from resources.resource_dict import resource_dict
from resources.base_resource import BaseResource
from messages.command_message import CommandMessage
from messages.answer_message import AnswerMessage
from agents.dataclasses.agent_lm_spec import AgentLMConfig
from resources.kali_env_resource import KaliEnvResource

class InitFilesResource(BaseResource):
    def __init__(self, resource_id: str) -> None:
        resource_dict[resource_id] = self
    def stop(args, kwargs):
        pass

class SetupResource(BaseResource):
    def __init__(self, resource_id: str) -> None:
        resource_dict[resource_id] = self
    def stop(args, kwargs):
        pass  
    
# Initialize KaliEnvResource for the testing instance
kali_env = KaliEnvResource(name=f"kali-env", volumes=None)

init_files = InitFilesResource("init-id")
task_server = SetupResource("task-id")

class TestExecutorAgent(unittest.TestCase):
    def setUp(self):
        # Create a mock config for the agent
        self.config = AgentLMConfig(
        self.config = AgentLMConfig(
            model="openai/o1-mini-2024-09-12",
            max_output_tokens=50,
            max_input_tokens=100,
            max_iterations_stored_in_memory=3,
            max_iterations_stored_in_memory=3,
            use_helm=True
        )

        # Initialize the agent
        self.agent = ExecutorAgent(config=self.config)

    def test_run_with_invalid_message_type(self):
        """
        Test run() raises exception when message not valid type
        """
        message = Mock(spec=AnswerMessage)
        with self.assertRaises(Exception) as context:
            self.agent.run(messages=[message])
        self.assertIn('Message not of an interpretable type', str(context.exception))

    def test_run_with_valid_message_type(self):
        """
        Test run() returns valid message
        """
        command_message = CommandMessage("command: ls")
        self.agent.execute = Mock()

        result = self.agent.run(messages=[command_message])

        # Check if execute() was called
        self.agent.execute.assert_called_once()

    def test_execute_calls_lm_and_runs_command(self):
        """
        Tests that execute() calls the LM and executes command.
        """
        # Simulate the call to call_lm
        self.agent.call_lm = Mock(return_value=CommandMessage("command: pwd"))

        result = self.agent.execute()

        self.assertEqual(result.observation.raw_output, "/app")

    def test_execute_in_env_success(self):
        """
        Test that execute_in_env runs the command successfully and returns an Observation.
        """
        message = CommandMessage("command: whoami")
        observation = self.agent.execute_in_env(message)

        self.assertEqual(observation.raw_output, "root")

    def test_execute_in_env_failure(self):
        """
        Test that exeucte_in_env handles command failure correctly.
        """
        message = CommandMessage("command: invalid_command")
        observation = self.agent.execute_in_env(message)

        self.assertIn("command not found", observation.raw_output)

if __name__ == "__main__":
    unittest.main()