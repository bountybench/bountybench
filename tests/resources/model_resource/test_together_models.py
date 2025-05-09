import unittest
from unittest.mock import MagicMock, patch

from resources.model_resource.together_models.together_models import TogetherModels


class TestTogetherModels(unittest.TestCase):
    """Test the Together models implementation."""

    def setUp(self):
        """Set up test environment."""
        # Create a patched version of Together models where we can control client responses
        self.patcher = patch(
            "resources.model_resource.together_models.together_models.Together"
        )
        self.mock_together = self.patcher.start()

        # Create a mock client with completion methods
        self.mock_client = MagicMock()
        self.mock_together.return_value = self.mock_client

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
        with patch.object(TogetherModels, "_api_key", return_value="fake-api-key"):
            self.together_models = TogetherModels()

    def tearDown(self):
        """Clean up test environment"""
        self.patcher.stop()

    def test_request_with_r1_model(self):
        """Test request with DeepSeek R1 model."""
        self.together_models.request(
            model="deepseek-ai/DeepSeek-R1",
            message="Test message",
            temperature=0.7,
            max_tokens=100,
            stop_sequences=["STOP"],
        )

        # Check that create was called with correct parameters
        self.mock_client.chat.completions.create.assert_called_once()
        call_args = self.mock_client.chat.completions.create.call_args[1]

        self.assertEqual(call_args["model"], "deepseek-ai/DeepSeek-R1")
        self.assertEqual(call_args["temperature"], 0.7)
        self.assertEqual(call_args["max_tokens"], 100)
        self.assertEqual(call_args["stop"], ["STOP"])

    def test_request_with_unsupported_model(self):
        """Test request with an unsupported model."""
        error_response = Exception("Model not found")
        self.mock_client.chat.completions.create.side_effect = error_response

        with self.assertRaises(Exception):
            self.together_models.request(
                model="unsupported-model",
                message="Test message",
                temperature=0.7,
                max_tokens=100,
                stop_sequences=["STOP"],
            )

    def test_request_with_erorr_code(self):
        """Test request with an invalid API key (401), check that the correct error status code is returned."""
        error_response = Exception("Invalid API key")
        error_response.status_code = 401
        self.mock_client.chat.completions.create.side_effect = error_response

        with self.assertRaises(Exception) as context:
            self.together_models.request(
                model="deepseek-ai/DeepSeek-R1",
                message="Test message",
                temperature=0.7,
                max_tokens=100,
                stop_sequences=["STOP"],
            )

        self.assertEqual(
            context.exception.status_code, 401
        )  # Check that the status code is 401
        self.assertEqual(
            str(context.exception), "Invalid API key"
        )  # Check that the error message is correct
