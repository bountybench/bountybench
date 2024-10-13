import unittest
import json
import os
from chat_chain import ChatChain

class TestChatChain(unittest.TestCase):
    
    def setUp(self):
        self.chat_chain = ChatChain()
        self.sample_message = {
            "role": "assistant",
            "content": "Hello, how can I assist you?"
        }
        self.file_path = "test_chat_chain.json"

    def tearDown(self):
        if os.path.exists(self.file_path):
            os.remove(self.file_path)

    def test_append(self):
        self.chat_chain.append(self.sample_message)
        self.assertEqual(len(self.chat_chain.chain), 1)
        self.assertEqual(self.chat_chain.chain[0]["role"], "assistant")
        self.assertEqual(self.chat_chain.chain[0]["content"], "Hello, how can I assist you?")

    def test_save_chat_chain_as_json(self):
        self.chat_chain.append(self.sample_message)
        self.chat_chain.save_chat_chain_as_json(self.file_path)
        
        self.assertTrue(os.path.exists(self.file_path))
        with open(self.file_path, "r") as file:
            data = json.load(file)
            self.assertEqual(data, [self.sample_message])

    def test_load_chat_chain(self):
        with open(self.file_path, "w") as file:
            json.dump([self.sample_message], file)
        
        self.chat_chain.load_chat_chain(self.file_path)
        self.assertEqual(len(self.chat_chain.chain), 1)
        self.assertEqual(self.chat_chain.chain[0]["role"], "assistant")
        self.assertEqual(self.chat_chain.chain[0]["content"], "Hello, how can I assist you?")

    def test_clear(self):
        self.chat_chain.append(self.sample_message)
        self.chat_chain.clear()
        self.assertEqual(len(self.chat_chain.chain), 0)

    def test_str(self):
        self.chat_chain.append(self.sample_message)
        expected_str = (
            "\n----------Message from assistant----------\nHello, how can I assist you?"
        )
        self.assertEqual(str(self.chat_chain), expected_str)

if __name__ == '__main__':
    unittest.main()