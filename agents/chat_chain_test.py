import unittest
import json
import os
from common import ChatChain, ChainLink


class TestChatChain(unittest.TestCase):

    
    def setUp(self):
        """This method runs before each test."""
        self.chat_chain = ChatChain()

    def test_append(self):
        """Test appending a message to the chat chain."""
        message = {"content": "Hello, this is another agent test.", "role": "agent"}
        self.chat_chain.append(message)
        self.assertEqual(len(self.chat_chain), 1)
        self.assertEqual(self.chat_chain[0].content, "Hello, this is another agent test.")
        self.assertEqual(self.chat_chain[0].role, "agent")
        self.assertEqual(self.chat_chain[0].seq_num, 0)

    def test_prepend(self):
        """Test prepending a message to the chat chain."""
        first_message = {"content": "Hello, this is the first message.", "role": "agent"}
        second_message = {"content": "This message is prepended.", "role": "assistant"}
        
        self.chat_chain.append(first_message)
        self.chat_chain.prepend(second_message)
        
        self.assertEqual(len(self.chat_chain), 2)
        self.assertEqual(self.chat_chain[0].content, "This message is prepended.")
        self.assertEqual(self.chat_chain[0].role, "assistant")
        self.assertEqual(self.chat_chain[0].seq_num, 0)

    def test_remove(self):
        """Test removing a message from the chat chain."""
        message = {"content": "This is a removable message.", "role": "agent"}
        self.chat_chain.append(message)
        self.chat_chain.remove(0)
        self.assertEqual(len(self.chat_chain), 0)

    def test_truncate(self):
        """Test truncating the chat chain."""
        message_1 = {"content": "Message 1", "role": "agent"}
        message_2 = {"content": "Message 2", "role": "assistant"}
        
        self.chat_chain.append(message_1)
        self.chat_chain.append(message_2)
        
        self.chat_chain.truncate(1)
        self.assertEqual(len(self.chat_chain), 1)
        self.assertEqual(self.chat_chain[0].content, "Message 1")

    def test_save_load_chat_chain(self):
        """Test saving and loading the chat chain from a JSON file."""
        message = {"content": "Hello, saving this.", "role": "agent"}
        self.chat_chain.append(message)

        # Save chat chain to a file
        file_path = "test_chat_chain.json"
        self.chat_chain.save_chat_chain_as_json(file_path)
        self.assertTrue(os.path.exists(file_path))

        # Load chat chain from a file
        loaded_chain = ChatChain.get_chat_chain_from_file(file_path)
        self.assertEqual(len(loaded_chain), 1)
        self.assertEqual(loaded_chain[0].content, "Hello, saving this.")
        
        # Cleanup
        os.remove(file_path)

    def test_clear(self):
        """Test clearing the chat chain."""
        message = {"content": "Clear me!", "role": "agent"}
        self.chat_chain.append(message)
        self.chat_chain.clear()
        self.assertEqual(len(self.chat_chain), 0)


if __name__ == "__main__":
    unittest.main()