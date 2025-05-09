import unittest
from unittest.mock import MagicMock, patch

import google.generativeai as gemini

from resources.model_resource.anthropic_models.anthropic_models import AnthropicModels
from resources.model_resource.google_models.google_models import GoogleModels
from resources.model_resource.model_response import ModelResponse
from resources.model_resource.openai_models.openai_models import OpenAIModels
from resources.model_resource.together_models.together_models import TogetherModels


class TestModelStatusCodes(unittest.TestCase):
    """Test status code handling in model providers"""

    def setUp(self):
        # Common setup for all tests
        self.mock_response = MagicMock()
        self.mock_response.choices = [MagicMock()]
        self.mock_response.choices[0].message.content = "Test response"
        self.mock_response.usage.prompt_tokens = 10
        self.mock_response.usage.completion_tokens = 20

    @patch.object(OpenAIModels, "create_client")
    @patch.object(OpenAIModels, "_api_key")
    def test_openai_success_response(self, mock_api_key, mock_create_client):
        """Test that successful OpenAI responses handle status codes correctly"""
        # Setup
        mock_api_key.return_value = "test_key"
        mock_client = MagicMock()

        # Set up the mock response for the responses API
        mock_response = MagicMock()
        mock_response.output_text = "Test response"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20
        mock_response.created_at = 0
        # In our mock, we need to make sure the response doesn't have a response attribute
        mock_response.response = None

        mock_client.responses.create.return_value = mock_response
        mock_create_client.return_value = mock_client

        # Test
        openai_model = OpenAIModels()
        with patch.object(openai_model, "tokenize", return_value=[]):
            with patch.object(openai_model, "decode", return_value=""):
                response = openai_model.request(
                    model="openai/gpt-4",
                    message="Test message",
                    temperature=0.7,
                    max_tokens=100,
                    stop_sequences=[],
                )

        # Verify
        self.assertIsInstance(response, ModelResponse)
        self.assertIsNone(response.status_code)  # Default no status code on success

    @patch.object(OpenAIModels, "create_client")
    @patch.object(OpenAIModels, "_api_key")
    def test_openai_error_response(self, mock_api_key, mock_create_client):
        """Test that OpenAI error responses extract status codes correctly"""
        # Setup
        mock_api_key.return_value = "test_key"
        mock_client = MagicMock()
        mock_error = Exception("API error")
        mock_error.status_code = 404
        mock_client.responses.create.side_effect = mock_error
        mock_create_client.return_value = mock_client

        # Test and Verify
        openai_model = OpenAIModels()
        with self.assertRaises(Exception) as context:
            openai_model.request(
                model="openai/gpt-4",
                message="Test message",
                temperature=0.7,
                max_tokens=100,
                stop_sequences=[],
            )

        # Verify the error has the status code attached
        self.assertTrue(hasattr(context.exception, "status_code"))
        self.assertEqual(context.exception.status_code, 404)

    @patch.object(AnthropicModels, "create_client")
    @patch.object(AnthropicModels, "_api_key")
    def test_anthropic_error_response(self, mock_api_key, mock_create_client):
        """Test that Anthropic error responses extract status codes correctly"""
        # Setup
        mock_api_key.return_value = "test_key"
        mock_client = MagicMock()

        # Create a mock response object and an error with response property
        mock_error = Exception("API error")
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_error.response = mock_response

        mock_client.messages.create.side_effect = mock_error
        mock_create_client.return_value = mock_client

        # Test and Verify
        anthropic_model = AnthropicModels()
        with self.assertRaises(Exception) as context:
            anthropic_model.request(
                model="anthropic/claude-3-opus-20240229",
                message="Test message",
                temperature=0.7,
                max_tokens=100,
                stop_sequences=[],
            )

        # Verify the error has the status code attached
        self.assertTrue(hasattr(context.exception, "status_code"))
        self.assertEqual(context.exception.status_code, 429)

    @patch.object(GoogleModels, "create_client")
    @patch.object(GoogleModels, "_api_key")
    def test_google_error_response(self, mock_api_key, mock_create_client):
        """Test that Google error responses extract status codes correctly"""
        # Setup for Google model test
        mock_api_key.return_value = "test_key"

        # Mock gemini configuration
        with patch.object(gemini, "configure") as mock_configure:
            # Create a mock error with status code - Google errors typically have a response attribute
            mock_error = Exception("API error")
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_error.response = mock_response

            # Mock the GenerativeModel instance
            mock_model = MagicMock()
            mock_model.generate_content.side_effect = mock_error
            mock_create_client.return_value = mock_model

            # Test and verify
            google_model = GoogleModels()
            with self.assertRaises(Exception) as context:
                google_model.request(
                    model="google/gemini-pro",
                    message="Test message",
                    temperature=0.7,
                    max_tokens=100,
                    stop_sequences=[],
                )

            # Our error extraction should attach a status_code
            self.assertTrue(hasattr(context.exception, "status_code"))
            self.assertEqual(context.exception.status_code, 403)

    @patch.object(TogetherModels, "create_client")
    @patch.object(TogetherModels, "_api_key")
    def test_together_error_response(self, mock_api_key, mock_create_client):
        """Test that Together API error responses extract status codes correctly"""
        # Setup
        mock_api_key.return_value = "test_key"
        mock_client = MagicMock()

        # Create a mock error with response property containing status_code
        mock_error = Exception("API error: model not found")
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_error.response = mock_response

        mock_client.chat.completions.create.side_effect = mock_error
        mock_create_client.return_value = mock_client

        # Test and verify
        together_model = TogetherModels()
        with self.assertRaises(Exception) as context:
            together_model.request(
                model="meta/llama-3-70b-instruct",
                message="Test message",
                temperature=0.7,
                max_tokens=100,
                stop_sequences=[],
            )

        # Verify the error has the status code attached
        self.assertTrue(hasattr(context.exception, "status_code"))
        self.assertEqual(context.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
