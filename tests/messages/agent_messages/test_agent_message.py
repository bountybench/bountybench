import unittest
from unittest.mock import MagicMock, patch, PropertyMock
import asyncio

from messages.agent_messages.agent_message import AgentMessage
from messages.action_messages.action_message import ActionMessage
from messages.message import Message
from messages.rerun_manager import RerunManager
from agents.agent_manager import AgentManager
from resources.resource_manager import ResourceManager

class TestAgentMessage(unittest.TestCase):

    def setUp(self):
        """
        Unit test setup.
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
    def test_current_children(self, mock_broadcast_update):
        """
        Test that current_children correctly retrieves the latest versions of actions.
        """
        agent_manager = MagicMock(spec=AgentManager)
        resource_manager = MagicMock(spec=ResourceManager)
        rerun_manager = RerunManager(agent_manager, resource_manager)

        agent_message = AgentMessage("test_id")
        action_msg1 = ActionMessage("test_id1", "test_msg1")
        action_msg4 = ActionMessage("test_id4", "test_msg4", prev=action_msg1)
        agent_message.add_child_message(action_msg1)
        agent_message.add_child_message(action_msg4)
        action_msg2 = asyncio.run(rerun_manager.edit_message(action_msg1, "test_msg2"))
        action_msg3 = asyncio.run(rerun_manager.edit_message(action_msg2, "test_msg3"))
        action_msg5 = asyncio.run(rerun_manager.edit_message(action_msg4, "test_msg5"))
        action_msg6 = ActionMessage("test_id6", "test_msg6", prev=action_msg3)
        action_msg3.parent.add_child_message(action_msg6)
        org_actions = agent_message.current_children
        parent2 = action_msg2.parent
        parent2_actions = parent2.current_children
        parent3 = action_msg3.parent
        parent3_actions = parent3.current_children
        parent5 = action_msg5.parent
        parent5_actions = parent5.current_children

        # Assertions
        self.assertEqual(len(agent_message.action_messages), 2)
        self.assertEqual(len(org_actions), 2)
        self.assertEqual(org_actions[0], action_msg1)
        self.assertEqual(org_actions[1], action_msg4)
        self.assertEqual(len(parent2.action_messages), 1)
        self.assertEqual(len(parent2_actions), 1)
        self.assertEqual(parent2_actions[0], action_msg2)
        self.assertEqual(len(parent3.action_messages), 2)
        self.assertEqual(len(parent3_actions), 2)
        self.assertEqual(parent3_actions[0], action_msg3)
        self.assertEqual(parent3_actions[1], action_msg6)
        self.assertEqual(len(parent5.action_messages), 2)
        self.assertEqual(len(parent5_actions), 2)
        self.assertEqual(parent5_actions[0], action_msg5.prev)
        self.assertEqual(parent5_actions[1], action_msg5)

    def test_add_child_message(self):
        """
        Test adding an action message to AgentMessage.
        """
        action_message = MagicMock(spec=ActionMessage)
        agent_message = AgentMessage("test_id")
        agent_message.add_child_message(action_message)

        # Assertions
        self.assertIn(action_message, agent_message.action_messages)
        action_message.set_parent.assert_called_once_with(agent_message)

    def test_agent_dict(self):
        """
        Test broadcast_dict method.
        """
        # Create an action message mock with to_broadcast_dict method
        action_message = MagicMock(spec=ActionMessage)
        action_message.to_broadcast_dict.return_value = {"action": "msg"}
        
        # Create an agent message and add the mocked action message
        agent_message = AgentMessage("test_id", "test_msg")
        agent_message._action_messages = [action_message]
        
        # Mock current_children to return our mocked action message
        with patch.object(AgentMessage, 'current_children', new_callable=PropertyMock) as mock_current_children:
            mock_current_children.return_value = [action_message]
            broadcast_dict = agent_message.to_broadcast_dict()

            # Assertions
            self.assertEqual(broadcast_dict["agent_id"], "test_id")
            self.assertEqual(broadcast_dict["message"], "test_msg")
            self.assertEqual(broadcast_dict["current_children"], [{"action": "msg"}])
            mock_current_children.assert_called_once()
            action_message.to_broadcast_dict.assert_called_once()

    def test_to_log_dict(self):
        """
        Test to_log_dict method.
        """
        action_message = MagicMock(spec=ActionMessage)
        action_message.to_log_dict.return_value = {"action": "msg"}
        
        agent_message = AgentMessage("test_id", "test_msg")
        agent_message._action_messages = [action_message]
        
        log_dict = agent_message.to_log_dict()

        # Assertions
        self.assertEqual(log_dict["agent_id"], "test_id")
        self.assertEqual(log_dict["message"], "test_msg")
        self.assertEqual(log_dict["action_messages"], [{"action": "msg"}])
        action_message.to_log_dict.assert_called_once()