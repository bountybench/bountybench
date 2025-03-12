import os
import unittest
from pathlib import Path
from typing import Tuple
from unittest.mock import patch

import dotenv

from resources.model_resource.services.api_key_service import (
    AUTH_SERVICE,
    verify_and_auth_api_key,
)

ENV_PATH = Path(dotenv.find_dotenv())
MODEL_PROVIDERS = ["helm", "openai", "anthropic"]


class TestApiKeyService(unittest.TestCase):
    def setUp(self):
        """
        Reset environment variables before each test.
        """
        self.mock_auth_service = self.create_mock_auth_service()
        os.environ.clear()
        print("\n")

    @staticmethod
    def create_mock_auth_service():
        """
        Create a mock authentication service
        """

        def mock_auth(
            api_key: str, model_name: str = None, verify_model: bool = False
        ) -> Tuple[bool, str]:
            if api_key.startswith("sk-test-"):
                if verify_model and model_name is not None:
                    if model_name.endswith("invalid-model"):
                        return False, f"Model {model_name} not found"
                return True, "Valid test key"
            if api_key.startswith("invalid-"):
                return False, "Invalid test key"
            return False, "Unknown key format"

        return mock_auth

    def test_valid_key_flow(self):
        """
        Test the complete validation flow with a valid key
        """

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
        """
        Test the complete validation flow with an invalid key
        """

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
        """
        Test the complete validation flow with a valid key and saving to .env
        """

        def input_args():
            yield "sk-test-valid123"
            yield "y"

        with patch("builtins.input", side_effect=input_args()):
            verify_and_auth_api_key(
                "openai/test_model", False, auth_service=self.mock_auth_service
            )

            mock_set_key.assert_called_once_with(
                ENV_PATH, "OPENAI_API_KEY", "sk-test-valid123", quote_mode="never"
            )

    def test_read_env_and_validate(self):
        """
        Test reading environment variables and validating them
        """
        dotenv.load_dotenv(ENV_PATH, override=True)
        for provider in MODEL_PROVIDERS:
            requested_api_key = f"{provider.upper()}_API_KEY"
            if requested_api_key in os.environ and os.environ[requested_api_key]:
                print(f"Found {requested_api_key} in environment, validating...")
                auth_service = AUTH_SERVICE[requested_api_key]
                # Test that invalid key will fail
                _ok, _message = auth_service("invalid-key")
                self.assertFalse(_ok)

                # Test that stored/correct key will pass
                _ok, _message = auth_service(os.environ[requested_api_key])
                self.assertTrue(_ok)
                print(f"{requested_api_key} validated.\n")
            else:
                print(f"{requested_api_key} not found in environment, skipping...\n")

    def test_model_verification_flag(self):
        """
        Test that the verify_model flag properly controls model verification
        """
        # When verify_model is False, a valid API key should pass even with an invalid model
        _ok, _message = self.mock_auth_service(
            "sk-test-valid123", "test/invalid-model", verify_model=False
        )
        self.assertTrue(_ok)

        # When verify_model is True, a valid API key with an invalid model should fail
        _ok, _message = self.mock_auth_service(
            "sk-test-valid123", "test/invalid-model", verify_model=True
        )
        self.assertFalse(_ok)

        # When verify_model is True but model_name is None, it should still pass
        _ok, _message = self.mock_auth_service(
            "sk-test-valid123", None, verify_model=True
        )
        self.assertTrue(_ok)

        # A valid API key with a valid model should always pass
        _ok, _message = self.mock_auth_service(
            "sk-test-valid123", "test/valid-model", verify_model=True
        )
        self.assertTrue(_ok)


if __name__ == "__main__":
    unittest.main()
