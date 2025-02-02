import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from messages.agent_messages.agent_message import AgentMessage
from messages.action_messages.action_message import ActionMessage
from messages.message import Message

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

    def test_current_actions_list(self):
        """
        Test that current_actions_list correctly retrieves the latest versions of actions.
        """
        # Mock ActionMessage instances
        action_msg1 = MagicMock(spec=ActionMessage)
        action_msg2 = MagicMock(spec=ActionMessage)
        action_msg3 = MagicMock(spec=ActionMessage)
        action_msg4 = MagicMock(spec=ActionMessage)
        action_msg5 = MagicMock(spec=ActionMessage)

        # Link actions and versions
        action_msg1.version_next = action_msg2
        action_msg2.version_prev = action_msg1
        action_msg2.version_next = action_msg3
        action_msg3.version_prev = action_msg2
        action_msg3.version_next = None  # Last version
        action_msg4.version_next = action_msg5
        action_msg5.version_prev = action_msg4
        action_msg5.version_next = None  # Last version
        action_msg3.next = action_msg4
        action_msg4.prev = action_msg3
        action_msg4.next = None  # Last action

        def side_effect_func(msg):
            if msg == action_msg1:
                return action_msg3  # Latest version of action_msg1
            elif msg == action_msg4:
                return action_msg5  # Latest version of action_msg4
            
        with patch.object(Message, 'get_latest_version') as mock_get_latest_version:
            mock_get_latest_version.side_effect = side_effect_func
            agent_message = AgentMessage("test_id")
            agent_message._action_messages = [action_msg1]

            current_actions = agent_message.current_actions_list

            # Assertions
            self.assertEqual(len(current_actions), 2)  # Should retrieve all actions
            self.assertEqual(current_actions[0], action_msg3)
            self.assertEqual(current_actions[1], action_msg5)

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
        with patch.object(AgentMessage, 'action_messages', new_callable=PropertyMock) as mock_action_messages, \
             patch.object(AgentMessage, 'current_actions_list', new_callable=PropertyMock) as mock_current_actions_list:
            
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
        with patch.object(Message, 'to_dict') as mock_super_to_dict, \
             patch.object(AgentMessage, 'agent_dict') as mock_agent_dict:
            
            mock_super_to_dict.return_value = {"super_key": "super_value"}
            mock_agent_dict.return_value = {"agent_key": "agent_value"}
            
            agent_message = AgentMessage("test_id", "test_msg")
            agent_dict = agent_message.to_dict()

            # Assertions
            self.assertEqual(agent_dict["super_key"], "super_value")
            self.assertEqual(agent_dict["agent_key"], "agent_value")
            mock_super_to_dict.assert_called_once()
            mock_agent_dict.assert_called_once()