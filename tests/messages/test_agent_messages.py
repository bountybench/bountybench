import unittest
from unittest.mock import MagicMock, patch
from typing import Optional, List

from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.executor_agent_message import ExecutorAgentMessage
from messages.agent_messages.exploit_agent_message import ExploitAgentMessage
from messages.agent_messages.patch_agent_message import PatchAgentMessage

from messages.action_messages.action_message import ActionMessage
from messages.message import Message

class TestAgentMessageClasses(unittest.TestCase):

    def setUp(self):
        patcher = patch("messages.message_utils.log_message")
        self.mock_log_message = patcher.start()
        self.addCleanup(patcher.stop)  # Ensure cleanup after tests
        # Mock Message and ActionMessage classes
        self.mock_message = MagicMock(spec=Message)
        self.mock_action_message = MagicMock(spec=ActionMessage)

        # Mock `get_latest_version` to always return the latest version of a message
        self.mock_message.get_latest_version = MagicMock(side_effect=lambda msg: msg if not hasattr(msg, 'version_next') else self.mock_message.get_latest_version(msg.version_next))

        # Mock ActionMessage instances with `next` and `prev`
        self.action_msg1 = MagicMock(spec=ActionMessage)
        self.action_msg2 = MagicMock(spec=ActionMessage)
        self.action_msg3 = MagicMock(spec=ActionMessage)

        # Link the messages in a chain
        self.action_msg1.next = self.action_msg2
        self.action_msg2.prev = self.action_msg1
        self.action_msg2.next = self.action_msg3
        self.action_msg3.prev = self.action_msg2
        self.action_msg3.next = None  # Last message

        # Mock `id` attributes for checking linkage
        self.action_msg1.id = "action1"
        self.action_msg2.id = "action1"  # Same ID, indicating a version chain
        self.action_msg3.id = "action1"

    def test_agent_message_is_message(self):
        """
        Ensure CommandMessage is a subclass of Message.
        """
        message = AgentMessage("test_id", "test_msg")
        self.assertIsInstance(message, Message)

    def test_initialization(self):
        """
        Test AgentMessage Initialization.
        """
        prev_message = self.mock_message
        msg = AgentMessage("test_id", "test_msg", prev=prev_message)

        self.assertEqual(msg.agent_id, "test_id")
        self.assertEqual(msg.message, "test_msg")
        self.assertEqual(msg.message_type, "AgentMessage")
        self.assertIs(msg.prev, prev_message)
        self.assertListEqual(msg.action_messages, [])

    @patch('messages.message.Message.get_latest_version')  # Mock get_latest_version at class level
    def test_current_actions_list(self, mock_get_latest_version):
        """
        Test that current_actions_list correctly retrieves the latest versions of actions.
        """
        # Mock `get_latest_version` to return the last message in the chain
        mock_get_latest_version.side_effect = lambda msg: self.action_msg3 if msg == self.action_msg1 else msg

        # Create an AgentMessage instance with action messages
        agent_msg = AgentMessage(agent_id="agent123")
        agent_msg._action_messages = [self.action_msg1]

        # Call current_actions_list
        current_actions = agent_msg.current_actions_list

        # Assertions
        self.assertEqual(len(current_actions), 3)  # Should retrieve all versions
        self.assertEqual(current_actions[0], self.action_msg3)  # Latest version of action1
        self.assertEqual(current_actions[1], self.action_msg2)  # Next version in chain
        self.assertEqual(current_actions[2], self.action_msg3)  # Last message

    def test_add_action_message(self):
        """
        Test adding an action message to AgentMessage.
        """
        agent_msg = AgentMessage(agent_id="agent123")
        agent_msg.add_action_message(self.action_msg1)

        # Check if the message was added
        self.assertIn(self.action_msg1, agent_msg.action_messages)
        self.action_msg1.set_parent.assert_called_once_with(agent_msg)

    def test_agent_dict(self):
        """
        Test agent_dict method.
        """
        agent_msg = AgentMessage(agent_id="agent123", message="Hello World")
        agent_msg._action_messages = [self.action_msg1, self.action_msg2]

        # Mock to_dict for action messages
        self.action_msg1.to_dict.return_value = {"action": "msg1"}
        self.action_msg2.to_dict.return_value = {"action": "msg2"}

        # Convert to dict
        agent_dict = agent_msg.agent_dict()

        # Assertions
        self.assertEqual(agent_dict["agent_id"], "agent123")
        self.assertEqual(agent_dict["message"], "Hello World")
        self.assertEqual(agent_dict["action_messages"], [{"action": "msg1"}, {"action": "msg2"}])
        self.assertIn("current_children", agent_dict)

    def test_to_dict(self):
        """
        Test to_dict method.
        """
        agent_msg = AgentMessage(agent_id="agent123")
        agent_msg.agent_dict = MagicMock(return_value={"agent": "data"})
        agent_msg.to_dict()

        # Ensure agent_dict is called
        agent_msg.agent_dict.assert_called_once()

if __name__ == "__main__":
    unittest.main()