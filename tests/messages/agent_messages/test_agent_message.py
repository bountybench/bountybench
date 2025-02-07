import asyncio
import unittest
from unittest.mock import MagicMock, PropertyMock, patch

from agents.agent_manager import AgentManager
from messages.action_messages.action_message import ActionMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message
from messages.rerun_manager import RerunManager
from resources.resource_manager import ResourceManager


class TestAgentMessage(unittest.TestCase):

    def setUp(self):
        """
        Unit test ingredient.
        """
        # Mock log_message
        patcher = patch("messages.message_utils.log_message")
        self.mock_log_message = patcher.start()
        self.addCleanup(patcher.stop)

    def test_agent_message_is_message(self):
        """
        Ensure AgentMessage is a subclass of Message.
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

    @patch("messages.message_utils.broadcast_update")
    def test_current_actions_list(self, mock_broadcast_update):
        """
        Test that current_actions_list correctly retrieves the latest versions of actions.
        """
        agent_manager = MagicMock(spec=AgentManager)
        resource_manager = MagicMock(spec=ResourceManager)
        rerun_manager = RerunManager(agent_manager, resource_manager)

        agent_message = AgentMessage("test_id")
        action_msg1 = ActionMessage("test_id1", "test_msg1")
        action_msg4 = ActionMessage("test_id4", "test_msg4", prev=action_msg1)
        agent_message.add_action_message(action_msg1)
        agent_message.add_action_message(action_msg4)

        action_msg2 = asyncio.run(rerun_manager.edit_message(action_msg1, "test_msg2"))
        action_msg3 = asyncio.run(rerun_manager.edit_message(action_msg2, "test_msg3"))
        action_msg5 = asyncio.run(rerun_manager.edit_message(action_msg4, "test_msg5"))
        current_actions = agent_message.current_actions_list

        # Assertions
        self.assertEqual(len(agent_message.action_messages), 5)
        self.assertEqual(len(current_actions), 1)
        self.assertEqual(current_actions[0], action_msg3)

    def test_add_action_message(self):
        """
        Test adding an action message to AgentMessage.
        """
        action_message = MagicMock(spec=ActionMessage)
        agent_message = AgentMessage("test_id")
        agent_message.add_action_message(action_message)

        # Assertions
        self.assertIn(action_message, agent_message.action_messages)
        action_message.set_parent.assert_called_once_with(agent_message)

    def test_agent_dict(self):
        """
        Test agent_dict method.
        """
        # Mock to_dict for action messages
        with (
            patch.object(
                AgentMessage, "action_messages", new_callable=PropertyMock
            ) as mock_action_messages,
            patch.object(
                AgentMessage, "current_actions_list", new_callable=PropertyMock
            ) as mock_current_actions_list,
        ):

            action_message = MagicMock(spec=ActionMessage)
            action_message.to_dict.return_value = {"action": "msg"}
            mock_action_messages.return_value = [action_message]
            mock_current_actions_list.return_value = [action_message]

            agent_message = AgentMessage("test_id", "test_msg")
            agent_dict = agent_message.agent_dict()

            # Assertions
            self.assertEqual(agent_dict["agent_id"], "test_id")
            self.assertEqual(agent_dict["action_messages"], [{"action": "msg"}])
            self.assertEqual(agent_dict["message"], "test_msg")
            mock_action_messages.assert_called()
            mock_current_actions_list.assert_called_once()
            action_message.to_dict.assert_called()
            self.assertIn("current_children", agent_dict)

    def test_to_dict(self):
        """
        Test to_dict method.
        """
        with (
            patch.object(Message, "to_dict") as mock_super_to_dict,
            patch.object(AgentMessage, "agent_dict") as mock_agent_dict,
        ):

            mock_super_to_dict.return_value = {"super_key": "super_value"}
            mock_agent_dict.return_value = {"agent_key": "agent_value"}

            agent_message = AgentMessage("test_id", "test_msg")
            agent_dict = agent_message.to_dict()

            # Assertions
            self.assertEqual(agent_dict["super_key"], "super_value")
            self.assertEqual(agent_dict["agent_key"], "agent_value")
            mock_super_to_dict.assert_called_once()
            mock_agent_dict.assert_called_once()

    # Sample test data for ActionMessage
    def create_action_message_dict(
        self, resource_id, message, additional_metadata=None
    ):
        return {
            "resource_id": resource_id,
            "message": message,
            "additional_metadata": additional_metadata or {},
            "prev": None,
            "next": None,
            "version_prev": None,
            "version_next": None,
            "parent": None,
            "current_id": str(id(message)),
            "timestamp": "2023-10-01T12:00:00Z",
        }

    # Sample test case for AgentMessage from_dict method
    def test_agent_message_from_dict(self):
        # Prepare test data with action messages
        action_message_dict1 = self.create_action_message_dict(
            "resource-1", "Action 1", {"key": "value"}
        )
        action_message_dict2 = self.create_action_message_dict("resource-2", "Action 2")

        # Prepare the main AgentMessage dict
        agent_message_data = {
            "agent_id": "agent-1",
            "message": "Agent message content",
            "prev": None,
            "next": None,
            "version_prev": None,
            "version_next": None,
            "parent": None,
            "current_id": str(id("agent-1")),
            "timestamp": "2023-10-01T12:00:00Z",
            "action_messages": [action_message_dict1, action_message_dict2],
        }

        # Create an AgentMessage instance using from_dict
        agent_message = AgentMessage.from_dict(agent_message_data)

        # Assertions to verify the properties of the created AgentMessage
        assert agent_message.agent_id == "agent-1"
        assert agent_message.message == "Agent message content"
        assert len(agent_message.action_messages) == 2

        # Verify the first action message
        action_message1 = agent_message.action_messages[0]
        assert action_message1.resource_id == "resource-1"
        assert action_message1.message == "Action 1"
        assert action_message1.additional_metadata == {"key": "value"}

        # Verify the second action message
        action_message2 = agent_message.action_messages[1]
        assert action_message2.resource_id == "resource-2"
        assert action_message2.message == "Action 2"
        assert action_message2.additional_metadata == {}

        # Verify the integrity of previous and next properties (None)
        assert agent_message.prev is None
        assert agent_message.next is None
