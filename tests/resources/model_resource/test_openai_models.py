import unittest
from unittest.mock import MagicMock, patch

from resources.model_resource.openai_models.openai_models import OpenAIModels


class TestOpenAIModels(unittest.TestCase):
    """Test the OpenAI models implementation, particularly suffix handling"""

    def setUp(self):
        """Set up test environment"""
        # Create a patched version of OpenAIModels where we can control client responses
        self.patcher = patch(
            "resources.model_resource.openai_models.openai_models.OpenAI"
        )
        self.mock_openai = self.patcher.start()

        # Create a mock client with completion methods
        self.mock_client = MagicMock()
        self.mock_openai.return_value = self.mock_client

        # Setup mock chat completions results
        self.mock_response = MagicMock()
        self.mock_response.choices = [MagicMock()]
        self.mock_response.choices[0].message = MagicMock()
        self.mock_response.choices[0].message.content = "Test response"
        self.mock_response.usage = MagicMock()
        self.mock_response.usage.prompt_tokens = 10
        self.mock_response.usage.completion_tokens = 5

        # Make the create method return our mock response
        self.mock_client.chat.completions.create.return_value = self.mock_response

        # Use a patched _api_key method to avoid real API calls
        with patch.object(OpenAIModels, "_api_key", return_value="fake-api-key"):
            self.openai_models = OpenAIModels()

    def tearDown(self):
        """Clean up test environment"""
        self.patcher.stop()

    def test_request_with_regular_model(self):
        """Test request method with a regular model (non-o1/o3)"""
        self.openai_models.request(
            model="openai/gpt-4",
            message="Test message",
            temperature=0.7,
            max_tokens=100,
            stop_sequences=["STOP"],
        )

        # Check that create was called with correct parameters
        self.mock_client.chat.completions.create.assert_called_once()
        call_args = self.mock_client.chat.completions.create.call_args[1]

        self.assertEqual(call_args["model"], "gpt-4")
        self.assertEqual(call_args["temperature"], 0.7)
        self.assertEqual(call_args["max_completion_tokens"], 100)
        self.assertEqual(call_args["stop"], ["STOP"])

    def test_request_with_o1_model(self):
        """Test request method with an o1 model"""
        self.openai_models.request(
            model="openai/o1-preview-2024-09-12",
            message="Test message",
            temperature=0.7,  # Should be ignored for o1 models
            max_tokens=100,
            stop_sequences=["STOP"],
        )

        # Check that create was called with correct parameters
        self.mock_client.chat.completions.create.assert_called_once()
        call_args = self.mock_client.chat.completions.create.call_args[1]

        self.assertEqual(call_args["model"], "o1-preview-2024-09-12")
        self.assertNotIn("temperature", call_args)  # Temperature should be excluded
        self.assertEqual(call_args["max_completion_tokens"], 100)
        self.assertEqual(call_args["stop"], ["STOP"])
        self.assertNotIn(
            "reasoning_effort", call_args
        )  # No reasoning_effort by default

    def test_request_with_o1_high_reasoning(self):
        """Test request method with an o1 model with high reasoning effort"""
        self.openai_models.request(
            model="openai/o1-preview-2024-09-12-high-reasoning-effort",
            message="Test message",
            temperature=0.7,
            max_tokens=100,
            stop_sequences=["STOP"],
        )

        # Check that create was called with correct parameters
        self.mock_client.chat.completions.create.assert_called_once()
        call_args = self.mock_client.chat.completions.create.call_args[1]

        # Check that model name was stripped correctly
        self.assertEqual(call_args["model"], "o1-preview-2024-09-12")
        self.assertNotIn("temperature", call_args)
        self.assertEqual(call_args["reasoning_effort"], "high")
        self.assertEqual(call_args["max_completion_tokens"], 100)
        self.assertEqual(call_args["stop"], ["STOP"])

    def test_request_with_o1_low_reasoning(self):
        """Test request method with an o1 model with low reasoning effort"""
        self.openai_models.request(
            model="openai/o1-preview-2024-09-12-low-reasoning-effort",
            message="Test message",
            temperature=0.7,
            max_tokens=100,
            stop_sequences=["STOP"],
        )

        # Check that create was called with correct parameters
        self.mock_client.chat.completions.create.assert_called_once()
        call_args = self.mock_client.chat.completions.create.call_args[1]

        # Check that model name was stripped correctly
        self.assertEqual(call_args["model"], "o1-preview-2024-09-12")
        self.assertNotIn("temperature", call_args)
        self.assertEqual(call_args["reasoning_effort"], "low")
        self.assertEqual(call_args["max_completion_tokens"], 100)
        self.assertEqual(call_args["stop"], ["STOP"])

    def test_request_with_o3_high_reasoning(self):
        """Test request method with an o3 model with high reasoning effort"""
        self.openai_models.request(
            model="openai/o3-mini-2025-01-31-high-reasoning-effort",
            message="Test message",
            temperature=0.7,
            max_tokens=100,
            stop_sequences=["STOP"],
        )

        # Check that create was called with correct parameters
        self.mock_client.chat.completions.create.assert_called_once()
        call_args = self.mock_client.chat.completions.create.call_args[1]

        # Check that model name was stripped correctly
        self.assertEqual(call_args["model"], "o3-mini-2025-01-31")
        self.assertNotIn("temperature", call_args)
        self.assertEqual(call_args["reasoning_effort"], "high")
        self.assertEqual(call_args["max_completion_tokens"], 100)
        self.assertEqual(call_args["stop"], ["STOP"])


if __name__ == "__main__":
    unittest.main()
