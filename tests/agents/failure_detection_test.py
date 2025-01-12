import unittest
from unittest.mock import MagicMock, patch

from agents.dataclasses.agent_lm_spec import AgentLMConfig

from agents.executor_agent.executor_agent import ExecutorAgent
from resources.kali_env_resource import KaliEnvResource
from messages.command_message import CommandMessage
from messages.failure_message import FailureMessage
from messages.message import Message

kali_env = KaliEnvResource(name=f"kali-env", volumes=None)


class TestExecutorAgent(unittest.TestCase):
    def setUp(self):
        # Define the AgentLMConfig with necessary parameters
        self.config = AgentLMConfig(
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

        mock_command_message = CommandMessage(
            message="Command: Test Message",
        )

        mock_execute.return_value = mock_command_message

        message: Message = self.agent.run(messages=[])
        message: Message = self.agent.run(messages=[])
        message: Message = self.agent.run(messages=[])
        message: Message = self.agent.run(messages=[])

        self.assertIsInstance(message, FailureMessage)
        self.assertEqual(
            message.message, "Failure Message")
    
    @patch.object(ExecutorAgent, 'execute')
    def test_run_with_failure_detection_less(self, mock_execute):
        self.agent = ExecutorAgent(
            config=self.config,
            failure_detection=True,
        )

        mock_command_message = CommandMessage(
            message="Command: Test Message",
        )

        mock_execute.return_value = mock_command_message

        message: Message = self.agent.run(messages=[])
        message: Message = self.agent.run(messages=[])
        message: Message = self.agent.run(messages=[])

        self.assertIsInstance(message, CommandMessage)
        self.assertEqual(message.command, "Test Message")
        self.assertEqual(message.message, "Command: Test Message")
    
    @patch.object(ExecutorAgent, 'execute')
    def test_run_with_failure_detection_change(self, mock_execute):
        self.agent = ExecutorAgent(
            config=self.config,
            failure_detection=True,
        )

        mock_command_message1 = CommandMessage(
            message="Command: Test Message",
        )

        mock_command_message2 = CommandMessage(
            message="Command: Random Random Random",
        )

        mock_execute.return_value = mock_command_message1

        message: Message = self.agent.run(messages=[])
        message: Message = self.agent.run(messages=[])
        message: Message = self.agent.run(messages=[])

        mock_execute.return_value = mock_command_message2

        message: Message = self.agent.run(messages=[])
        message: Message = self.agent.run(messages=[])

        self.assertIsInstance(message, CommandMessage)
        self.assertEqual(message.command, "Random Random Random")
        self.assertEqual(message.message, "Command: Random Random Random")
        self.assertEqual(len(self.agent.message_history.messages), 5)

        message: Message = self.agent.run(messages=[])
        message: Message = self.agent.run(messages=[])

        self.assertIsInstance(message, FailureMessage)
        self.assertEqual(
            message.message, "Failure Message")
        self.assertEqual(len(self.agent.message_history.messages), 6)
    
    @patch.object(ExecutorAgent, 'execute')
    def test_run_with_failure_detection_vary(self, mock_execute):
        self.agent = ExecutorAgent(
            config=self.config,
            failure_detection=True,
        )

        mock_command_message = CommandMessage(
            message="Command: Test Message",
        )

        mock_command_message1 = CommandMessage(
            message="Command: Test Message1",
        )

        mock_command_message2 = CommandMessage(
            message="Command: Test Message2",
        )

        mock_command_message3 = CommandMessage(
            message="Command: Test Message3",
        )

        mock_execute.return_value = mock_command_message1
        message: Message = self.agent.run(messages=[])

        mock_execute.return_value = mock_command_message2
        message: Message = self.agent.run(messages=[])

        mock_execute.return_value = mock_command_message3
        message: Message = self.agent.run(messages=[])

        mock_execute.return_value = mock_command_message
        message: Message = self.agent.run(messages=[])

        self.assertIsInstance(message, FailureMessage)
        self.assertEqual(
            message.message, "Failure Message")
        self.assertEqual(len(self.agent.message_history.messages), 3)

if __name__ == '__main__':
    unittest.main()
