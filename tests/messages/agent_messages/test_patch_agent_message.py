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
        patch_agent_message = PatchAgentMessage("test_id", "test_msg", True, "/patch", prev_message)

        # Assertions
        self.assertEqual(patch_agent_message.agent_id, "test_id")
        self.assertEqual(patch_agent_message.message, "test_msg")
        self.assertEqual(patch_agent_message.success, True)
        self.assertEqual(patch_agent_message.patch_files_dir, "/patch")
        self.assertIs(patch_agent_message.prev, prev_message)

    def test_to_broadcast_dict(self):
        """
        Test to_broadcast_dict method.
        """
        # Create a patch agent message
        patch_agent_message = PatchAgentMessage(
            "test_id", 
            "test_msg", 
            success=True, 
            patch_files_dir="/patch"
        )
        
        # Call to_broadcast_dict
        broadcast_dict = patch_agent_message.to_broadcast_dict()

        # Assertions
        self.assertEqual(broadcast_dict["agent_id"], "test_id")
        self.assertEqual(broadcast_dict["message"], "test_msg")
        self.assertEqual(broadcast_dict["success"], True)
        self.assertEqual(broadcast_dict["patch_files_dir"], "/patch")
        self.assertIn("current_children", broadcast_dict)

    def test_to_log_dict(self):
        """
        Test to_log_dict method.
        """
        # Create action message mock with to_log_dict method
        action_message = MagicMock(spec=ActionMessage)
        action_message.to_log_dict.return_value = {"action": "msg"}
        
        # Create patch agent message
        patch_agent_message = PatchAgentMessage(
            "test_id", 
            "test_msg", 
            success=True, 
            patch_files_dir="/patch"
        )
        patch_agent_message._action_messages = [action_message]
        
        # Call to_log_dict
        log_dict = patch_agent_message.to_log_dict()

        # Assertions
        self.assertEqual(log_dict["agent_id"], "test_id")
        self.assertEqual(log_dict["message"], "test_msg")
        self.assertEqual(log_dict["success"], True)
        self.assertEqual(log_dict["patch_files_dir"], "/patch")
        self.assertEqual(log_dict["action_messages"], [{"action": "msg"}])
        action_message.to_log_dict.assert_called_once()