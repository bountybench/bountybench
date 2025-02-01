import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.executor_agent_message import ExecutorAgentMessage

from messages.action_messages.action_message import ActionMessage
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

    def test_message_property(self):
        """
        Test that message property correctly concatenates action messages.
        """
        expected_message = "Hello World! How are you?"
        with patch.object(AgentMessage, 'current_actions_list', new_callable=PropertyMock) as mock_super_current_actions_list:
            mock_action_message1 = MagicMock(spec=ActionMessage)
            mock_action_message1.message = "Hello "
            mock_action_message2 = MagicMock(spec=ActionMessage)
            mock_action_message2.message = "World!"
            mock_action_message3 = MagicMock(spec=ActionMessage)
            mock_action_message3.message = " How are you?"
            mock_super_current_actions_list.return_value = [
                mock_action_message1, mock_action_message2, mock_action_message3
            ]
            agent_message = MagicMock(spec=AgentMessage)
            executor_agent_message = ExecutorAgentMessage(agent_message)
            self.assertEqual(executor_agent_message.message, expected_message)

    def test_message_property_with_empty_list(self):
        """
        Test message property when there are no action messages.
        """
        expected_message = ""
        with patch.object(AgentMessage, 'current_actions_list', new_callable=PropertyMock) as mock_super_current_actions_list:
            mock_super_current_actions_list.return_value = []
            agent_message = MagicMock(spec=AgentMessage)
            executor_agent_message = ExecutorAgentMessage(agent_message)
            self.assertEqual(executor_agent_message.message, expected_message)

    def test_message_property_with_none_messages(self):
        """
        Test message property when some action messages are None.
        """
        expected_message = "Hello  How are you?"
        with patch.object(AgentMessage, 'current_actions_list', new_callable=PropertyMock) as mock_super_current_actions_list:
            mock_action_message1 = MagicMock(spec=ActionMessage)
            mock_action_message1.message = "Hello "
            mock_action_message2 = MagicMock(spec=ActionMessage)
            mock_action_message2.message = None
            mock_action_message3 = MagicMock(spec=ActionMessage)
            mock_action_message3.message = " How are you?"
            mock_super_current_actions_list.return_value = [
                mock_action_message1, mock_action_message2, mock_action_message3
            ]
            agent_message = MagicMock(spec=AgentMessage)
            executor_agent_message = ExecutorAgentMessage(agent_message)
            self.assertEqual(executor_agent_message.message, expected_message)