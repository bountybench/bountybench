from resources.model_resource.services.api_key_service import (
    _auth_helm_api_key,
    _auth_openai_api_key,
    _auth_anthropic_api_key,
    verify_and_auth_api_key,
)
from typing import Tuple
import os

import unittest
from unittest.mock import patch

import dotenv
from pathlib import Path

env_path = Path(dotenv.find_dotenv())


# Unit tests for API key authentication
def test_auth_helm_api_key():
    assert _auth_helm_api_key("obviously_invalid_api_key", "")[0] is False

    valid_api_key = input("Enter a valid HELM API key: ")
    assert _auth_helm_api_key(valid_api_key)[0] is True


def test_auth_openai_api_key():
    assert _auth_openai_api_key("obviously_invalid_api_key")[0] is False

    valid_api_key = input("Enter a valid OpenAI API key: ")
    assert _auth_openai_api_key(valid_api_key)[0] is True


def test_auth_anthropic_api_key():
    assert _auth_anthropic_api_key("obviously_invalid_api_key")[0] is False

    valid_api_key = input("Enter a valid Anthropic API key: ")
    assert _auth_anthropic_api_key(valid_api_key)[0] is True


# Tests
class TestApiKeyService(unittest.TestCase):
    def setUp(self):
        """Reset environment variables before each test."""
        self.mock_auth_service = self.create_mock_auth_service()
        os.environ.clear()
        print("\n")

    @staticmethod
    def create_mock_auth_service():
        """Create a mock authentication service"""

        def mock_auth(api_key: str) -> Tuple[bool, str]:
            if api_key.startswith("sk-test-"):
                return True, "Valid test key"
            if api_key.startswith("invalid-"):
                return False, "Invalid test key"
            return False, "Unknown key format"

        return mock_auth

    def test_valid_key_flow(self):
        """Test the complete validation flow with a valid key"""

        def input_args():
            yield "sk-test-valid123"
            yield "n"

        with (
            patch("builtins.input", side_effect=input_args()),
            patch("dotenv.set_key") as mock_set_key,
        ):
            verify_and_auth_api_key(
                "openai/test_model", False, auth_service=self.mock_auth_service
            )

            mock_set_key.assert_not_called()

    def test_invalid_key_flow(self):
        """Test the complete validation flow with an invalid key"""

        def input_args():
            yield "invalid-123"
            yield "sk-test-valid123"
            yield "n"

        with (
            patch("builtins.input", side_effect=input_args()),
            patch("dotenv.set_key") as mock_set_key,
        ):
            verify_and_auth_api_key(
                "openai/test_model", False, auth_service=self.mock_auth_service
            )

            mock_set_key.assert_not_called()

    @patch("resources.model_resource.services.api_key_service.set_key")
    def test_valid_key_flow_save(self, mock_set_key):
        """Test the complete validation flow with a valid key and saving to .env"""

        def input_args():
            yield "sk-test-valid123"
            yield "y"

        with patch("builtins.input", side_effect=input_args()):
            verify_and_auth_api_key(
                "openai/test_model", False, auth_service=self.mock_auth_service
            )

            mock_set_key.assert_called_once_with(
                env_path, "OPENAI_API_KEY", "sk-test-valid123", quote_mode="never"
            )


if __name__ == "__main__":
    unittest.main()

    # Uncomment below to authenticate with actual model provider endpoints
    # test_auth_helm_api_key()
    # print(" - auth_helm_api_key passed")

    # test_auth_openai_api_key()
    # print(" - auth_openai_api_key passed")

    # test_auth_anthropic_api_key()
    # print(" - auth_anthropic_api_key passed")
