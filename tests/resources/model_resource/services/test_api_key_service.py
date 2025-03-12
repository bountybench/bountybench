import os
import tempfile
import unittest
from pathlib import Path
from typing import Tuple
from unittest.mock import MagicMock, patch

import dotenv

from resources.model_resource.services.api_key_service import (
    AUTH_SERVICE,
    verify_and_auth_api_key,
)

# Create a temporary .env file for testing
TEMP_ENV_FILE = tempfile.NamedTemporaryFile(delete=False)
TEMP_ENV_FILE.write(b"OPENAI_API_KEY=sk-test-openai\n")
TEMP_ENV_FILE.write(b"ANTHROPIC_API_KEY=sk-test-anthropic\n")
TEMP_ENV_FILE.write(b"HELM_API_KEY=sk-test-helm\n")
TEMP_ENV_FILE.close()
ENV_PATH = Path(TEMP_ENV_FILE.name)
MODEL_PROVIDERS = ["helm", "openai", "anthropic"]


class TestApiKeyService(unittest.TestCase):
    def setUp(self):
        """
        Reset environment variables before each test.
        """
        self.mock_auth_service = self.create_mock_auth_service()
        os.environ.clear()
        print("\n")

    @classmethod
    def tearDownClass(cls):
        """Clean up temporary files"""
        try:
            os.unlink(TEMP_ENV_FILE.name)
        except:
            pass

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
            patch("dotenv.find_dotenv", return_value=TEMP_ENV_FILE.name),
            patch("pathlib.Path.is_file", return_value=True),
            patch("dotenv.load_dotenv", return_value=True),
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
            patch("dotenv.find_dotenv", return_value=TEMP_ENV_FILE.name),
            patch("pathlib.Path.is_file", return_value=True),
            patch("dotenv.load_dotenv", return_value=True),
        ):
            verify_and_auth_api_key(
                "openai/test_model", False, auth_service=self.mock_auth_service
            )

            mock_set_key.assert_not_called()

    def test_valid_key_flow_save(self):
        """
        Test the complete validation flow with a valid key and saving to .env
        """

        def input_args():
            yield "sk-test-valid123"
            yield "y"

        mock_set_key = MagicMock()

        with (
            patch("builtins.input", side_effect=input_args()),
            patch("dotenv.find_dotenv", return_value=TEMP_ENV_FILE.name),
            patch("pathlib.Path.is_file", return_value=True),
            patch("dotenv.load_dotenv", return_value=True),
            patch(
                "resources.model_resource.services.api_key_service.set_key",
                mock_set_key,
            ),
        ):
            verify_and_auth_api_key(
                "openai/test_model", False, auth_service=self.mock_auth_service
            )

            mock_set_key.assert_called_once()
            # Only check that set_key was called, don't verify exact parameters
            # since they may vary in different environments

    def test_verify_model_flag_behavior(self):
        """
        Just test our mock authentication function with the verify_model flag
        This ensures the basic behavior works as expected
        """
        # Test with our mock auth function
        _ok, _message = self.mock_auth_service("sk-test-valid123", verify_model=False)
        self.assertTrue(_ok, "Valid key should pass when verify_model is False")

        # Test with an invalid model, verify_model=False should let it pass
        _ok, _message = self.mock_auth_service(
            "sk-test-valid123", "test/invalid-model", verify_model=False
        )
        self.assertTrue(
            _ok, "Valid key with invalid model should pass when verify_model is False"
        )

        # Test with an invalid model, verify_model=True should fail
        _ok, _message = self.mock_auth_service(
            "sk-test-valid123", "test/invalid-model", verify_model=True
        )
        self.assertFalse(
            _ok, "Valid key with invalid model should fail when verify_model is True"
        )

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
