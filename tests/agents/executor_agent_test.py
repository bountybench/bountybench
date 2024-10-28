import unittest
from unittest.mock import Mock, patch
from agents.executor_agent.executor_agent import ExecutorAgent    
from models.model_response import ModelResponse
from resources.resource_dict import resource_dict
from resources.base_resource import BaseResource
from responses.command_response import CommandResponse
from responses.answer_response import AnswerResponse
from agents.dataclasses.agent_spec import AgentConfig
from resources.kali_env_resource import KaliEnvResource

class InitFilesResource(BaseResource):
    def __init__(self, resource_id: str) -> None:
        resource_dict[resource_id] = self
    def stop(args, kwargs):
        pass

class TaskServerResource(BaseResource):
    def __init__(self, resource_id: str) -> None:
        resource_dict[resource_id] = self
    def stop(args, kwargs):
        pass  
    
# Initialize KaliEnvResource for the testing instance
kali_env = KaliEnvResource(name=f"kali-env", volumes=None)

init_files = InitFilesResource("init-id")
task_server = TaskServerResource("task-id")

class TestExecutorAgent(unittest.TestCase):
    def setUp(self):
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
        self.agent = ExecutorAgent(config=self.config)

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
        # Simulate the call to call_lm
        self.agent.call_lm = Mock(return_value=CommandResponse("command: pwd"))

        result = self.agent.execute()

        self.assertEqual(result.observation.raw_output, "/app")

    def test_execute_in_env_success(self):
        """
        Test that execute_in_env runs the command successfully and returns an Observation.
        """
        response = CommandResponse("command: whoami")
        observation = self.agent.execute_in_env(response)

        self.assertEqual(observation.raw_output, "root")

    def test_execute_in_env_failure(self):
        """
        Test that exeucte_in_env handles command failure correctly.
        """
        response = CommandResponse("command: invalid_command")
        observation = self.agent.execute_in_env(response)

        self.assertIn("command not found", observation.raw_output)

if __name__ == "__main__":
    unittest.main()
