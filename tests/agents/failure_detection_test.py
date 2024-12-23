import unittest
from unittest.mock import MagicMock, patch

from agents.dataclasses.agent_spec import AgentConfig

from agents.executor_agent.executor_agent import ExecutorAgent
from resources.kali_env_resource import KaliEnvResource
from responses.command_response import CommandResponse
from responses.failure_response import FailureResponse
from responses.response import Response

kali_env = KaliEnvResource(name=f"kali-env", volumes=None)


class TestExecutorAgent(unittest.TestCase):
    def setUp(self):
        # Define the AgentConfig with necessary parameters
        self.config = AgentConfig(
            max_iterations_stored_in_memory=100,
            max_input_tokens=500,
            model="test-model",
            max_output_tokens=150,
            use_helm=False
        )

    @patch.object(ExecutorAgent, 'execute')
    def test_run_with_failure_detection(self, mock_execute):
        self.agent = ExecutorAgent(
            config=self.config,
            failure_detection=True,
        )

        mock_command_response = CommandResponse(
            response="Command: Test Response",
        )

        mock_execute.return_value = mock_command_response

        response: Response = self.agent.run(responses=[])
        response: Response = self.agent.run(responses=[])
        response: Response = self.agent.run(responses=[])
        response: Response = self.agent.run(responses=[])

        self.assertIsInstance(response, FailureResponse)
        self.assertEqual(
            response.response, "Failure Response")
    
    @patch.object(ExecutorAgent, 'execute')
    def test_run_with_failure_detection_less(self, mock_execute):
        self.agent = ExecutorAgent(
            config=self.config,
            failure_detection=True,
        )

        mock_command_response = CommandResponse(
            response="Command: Test Response",
        )

        mock_execute.return_value = mock_command_response

        response: Response = self.agent.run(responses=[])
        response: Response = self.agent.run(responses=[])
        response: Response = self.agent.run(responses=[])

        self.assertIsInstance(response, CommandResponse)
        self.assertEqual(response.command, "Test Response")
        self.assertEqual(response.response, "Command: Test Response")
    
    @patch.object(ExecutorAgent, 'execute')
    def test_run_with_failure_detection_change(self, mock_execute):
        self.agent = ExecutorAgent(
            config=self.config,
            failure_detection=True,
        )

        mock_command_response1 = CommandResponse(
            response="Command: Test Response",
        )

        mock_command_response2 = CommandResponse(
            response="Command: Random Random Random",
        )

        mock_execute.return_value = mock_command_response1

        response: Response = self.agent.run(responses=[])
        response: Response = self.agent.run(responses=[])
        response: Response = self.agent.run(responses=[])

        mock_execute.return_value = mock_command_response2

        response: Response = self.agent.run(responses=[])
        response: Response = self.agent.run(responses=[])

        self.assertIsInstance(response, CommandResponse)
        self.assertEqual(response.command, "Random Random Random")
        self.assertEqual(response.response, "Command: Random Random Random")
        self.assertEqual(len(self.agent.response_history.responses), 5)

        response: Response = self.agent.run(responses=[])
        response: Response = self.agent.run(responses=[])

        self.assertIsInstance(response, FailureResponse)
        self.assertEqual(
            response.response, "Failure Response")
        self.assertEqual(len(self.agent.response_history.responses), 6)
    
    @patch.object(ExecutorAgent, 'execute')
    def test_run_with_failure_detection_vary(self, mock_execute):
        self.agent = ExecutorAgent(
            config=self.config,
            failure_detection=True,
        )

        mock_command_response = CommandResponse(
            response="Command: Test Response",
        )

        mock_command_response1 = CommandResponse(
            response="Command: Test Response1",
        )

        mock_command_response2 = CommandResponse(
            response="Command: Test Response2",
        )

        mock_command_response3 = CommandResponse(
            response="Command: Test Response3",
        )

        mock_execute.return_value = mock_command_response1
        response: Response = self.agent.run(responses=[])

        mock_execute.return_value = mock_command_response2
        response: Response = self.agent.run(responses=[])

        mock_execute.return_value = mock_command_response3
        response: Response = self.agent.run(responses=[])

        mock_execute.return_value = mock_command_response
        response: Response = self.agent.run(responses=[])

        self.assertIsInstance(response, FailureResponse)
        self.assertEqual(
            response.response, "Failure Response")
        self.assertEqual(len(self.agent.response_history.responses), 3)

if __name__ == '__main__':
    unittest.main()
