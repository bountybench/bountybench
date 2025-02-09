import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.patch_agent_message import PatchAgentMessage

from messages.action_messages.action_message import ActionMessage
from messages.message import Message

class TestPatchAgentMessage(unittest.TestCase):

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
        Test that PatchAgentMessage correctly inherits from AgentMessage.
        """
        patch_agent_message = PatchAgentMessage("test_id", "test_msg")
        self.assertIsInstance(patch_agent_message, AgentMessage)
        self.assertIsInstance(patch_agent_message, Message)

    def test_initialization(self):
        """
        Test PatchAgentMessage Initialization.
        """
        prev_message = MagicMock(spec=AgentMessage)
        patch_agent_message = PatchAgentMessage("test_id", "test_msg", True, "\patch", prev_message)

        # Assertions
        self.assertEqual(patch_agent_message.agent_id, "test_id")
        self.assertEqual(patch_agent_message.message, "test_msg")
        self.assertEqual(patch_agent_message.success, True)
        self.assertEqual(patch_agent_message.patch_files_dir, "\patch")
        self.assertIs(patch_agent_message.prev, prev_message)

    def test_to_dict(self):
        """
        Test to_dict method.
        """
        with patch.object(Message, 'to_dict') as mock_super_to_dict, \
             patch.object(AgentMessage, 'agent_dict') as mock_agent_dict:
            
            mock_super_to_dict.return_value = {"super_key": "super_value"}
            mock_agent_dict.return_value = {"agent_key": "agent_value"}
            
            patch_agent_message = PatchAgentMessage("test_id", "test_msg", True, "\patch")
            patch_agent_dict = patch_agent_message.to_dict()

            # Assertions
            self.assertEqual(patch_agent_dict["super_key"], "super_value")
            self.assertEqual(patch_agent_dict["agent_key"], "agent_value")
            self.assertEqual(patch_agent_dict["success"], True)
            self.assertEqual(patch_agent_dict["patch_files_dir"], "\patch")
            mock_super_to_dict.assert_called_once()
            mock_agent_dict.assert_called_once()