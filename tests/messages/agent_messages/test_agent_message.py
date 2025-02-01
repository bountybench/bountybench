import unittest
from unittest.mock import MagicMock, patch

from messages.agent_messages.agent_message import AgentMessage
from messages.action_messages.action_message import ActionMessage
from messages.message import Message

class TestAgentMessageClasses(unittest.TestCase):

    def setUp(self):
        """
        Unit test ingredient.
        """
        # Mock log_message
        patcher = patch("messages.message_utils.log_message")
        self.mock_log_message = patcher.start()
        self.addCleanup(patcher.stop)

        # Mock Message and ActionMessage classes
        self.mock_message = MagicMock(spec=Message)
        self.mock_action_message = MagicMock(spec=ActionMessage)

        # Mock ActionMessage instances
        self.action_msg1 = MagicMock(spec=ActionMessage)
        self.action_msg2 = MagicMock(spec=ActionMessage)
        self.action_msg3 = MagicMock(spec=ActionMessage)
        self.action_msg4 = MagicMock(spec=ActionMessage)
        self.action_msg5 = MagicMock(spec=ActionMessage)

        # Link actions and versions
        self.action_msg1.version_next = self.action_msg2
        self.action_msg2.version_prev = self.action_msg1
        self.action_msg2.version_next = self.action_msg3
        self.action_msg3.version_prev = self.action_msg2
        self.action_msg3.version_next = None  # Last version
        self.action_msg4.version_next = self.action_msg5
        self.action_msg5.version_prev = self.action_msg4
        self.action_msg5.version_next = None  # Last version
        self.action_msg3.next = self.action_msg4
        self.action_msg4.prev = self.action_msg3
        self.action_msg4.next = None  # Last action

    def test_agent_message_is_message(self):
        """
        Ensure CommandMessage is a subclass of Message.
        """
        agent_message = AgentMessage("test_id", "test_msg")
        self.assertIsInstance(agent_message, Message)

    def test_initialization(self):
        """
        Test AgentMessage Initialization.
        """
        prev_message = MagicMock(spec=Message)
        agent_message = AgentMessage("test_id", "test_msg", prev_message)

        # Assertions
        self.assertEqual(agent_message.agent_id, "test_id")
        self.assertEqual(agent_message.message, "test_msg")
        self.assertEqual(agent_message.message_type, "AgentMessage")
        self.assertIs(agent_message.prev, prev_message)
        self.assertListEqual(agent_message.action_messages, [])

    @patch('messages.message.Message.get_latest_version')
    def test_current_actions_list(self, mock_get_latest_version):
        """
        Test that current_actions_list correctly retrieves the latest versions of actions.
        """
        # Hardcode `get_latest_version` to return the lastest actions in the chain
        mock_get_latest_version.side_effect = lambda msg: self.action_msg3 if msg == self.action_msg1 else self.action_msg5

        # Create an AgentMessage instance with action messages
        agent_msg = AgentMessage("test_id")
        agent_msg._action_messages = [self.action_msg1]

        # Call current_actions_list
        current_actions = agent_msg.current_actions_list

        # Assertions
        self.assertEqual(len(current_actions), 2)  # Should retrieve all actions
        self.assertEqual(current_actions[0], self.action_msg3)  # Latest version of action1
        self.assertEqual(current_actions[1], self.action_msg5)  # Latest version of action4

    def test_add_action_message(self):
        """
        Test adding an action message to AgentMessage.
        """
        agent_msg = AgentMessage("test_id")
        agent_msg.add_action_message(self.action_msg1)

        # Assertions
        self.assertIn(self.action_msg1, agent_msg.action_messages)
        self.action_msg1.set_parent.assert_called_once_with(agent_msg)

    def test_agent_dict(self):
        """
        Test agent_dict method.
        """
        agent_msg = AgentMessage("test_id", "test_msg")
        agent_msg._action_messages = [self.action_msg1, self.action_msg2]

        # Mock to_dict for action messages
        self.action_msg1.to_dict.return_value = {"action": "msg1"}
        self.action_msg2.to_dict.return_value = {"action": "msg2"}
        agent_dict = agent_msg.agent_dict()

        # Assertions
        self.assertEqual(agent_dict["agent_id"], "test_id")
        self.assertEqual(agent_dict["action_messages"], [{"action": "msg1"}, {"action": "msg2"}])
        self.assertEqual(agent_dict["message"], "test_msg")
        self.assertIn("current_children", agent_dict)

    @patch.object(Message, 'to_dict')
    def test_to_dict(self, mock_super_to_dict):
        """
        Test to_dict method.
        """
        # Define the return value for super().to_dict()
        mock_super_to_dict.return_value = {"super_key": "super_value"}

        # Mock agent_dict
        agent_msg = AgentMessage("test_id", "test_msg")
        agent_msg.agent_dict = MagicMock(return_value={"agent_key": "agent_data"})
        agent_dict = agent_msg.to_dict()

        # Assertions
        self.assertEqual(agent_dict["super_key"], "super_value")
        self.assertEqual(agent_dict["agent_key"], "agent_data")
        agent_msg.agent_dict.assert_called_once()
        mock_super_to_dict.assert_called_once()