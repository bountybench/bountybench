import unittest
from unittest.mock import MagicMock, PropertyMock, patch

from messages.action_messages.action_message import ActionMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.executor_agent_message import ExecutorAgentMessage
from messages.message import Message


class TestExecutorAgentMessage(unittest.TestCase):

    def setUp(self):
        """
        Setup common mocks for all test cases.
        """
        # Mock log_message
        patcher = patch("messages.message_utils.log_message")
        self.mock_log_message = patcher.start()
        self.addCleanup(patcher.stop)

    def test_inheritance(self):
        """
        Test that ExecutorAgentMessage correctly inherits from AgentMessage.
        """
        agent_message = MagicMock(spec=AgentMessage)
        executor_agent_message = ExecutorAgentMessage(agent_message)
        self.assertIsInstance(executor_agent_message, AgentMessage)
        self.assertIsInstance(executor_agent_message, Message)
