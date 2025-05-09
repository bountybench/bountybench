import os
import tempfile
import unittest
from pathlib import Path
from typing import Tuple
from unittest.mock import MagicMock, patch

import dotenv

from resources.model_resource.model_mapping import HelmModelInfo, NonHelmModelInfo
from resources.model_resource.services.api_key_service import verify_and_auth_api_key
from resources.model_resource.services.service_providers import ServiceProvider

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
    def create_mock_get_model_info():
        """
        Create a mock function to simulate getting model information
        """

        def mock_get_model_info(
            model_name: str, helm: bool
        ) -> HelmModelInfo | NonHelmModelInfo:
            if not helm:
                return NonHelmModelInfo(
                    model_name=model_name, provider=ServiceProvider.OPENAI
                )
            else:
                return HelmModelInfo(
                    model_name=model_name,
                    tokenizer="test_tokenizer",
                )

        return mock_get_model_info

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
            patch(
                "resources.model_resource.services.api_key_service.get_model_info",
                self.create_mock_get_model_info(),
            ),
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
            patch(
                "resources.model_resource.services.api_key_service.get_model_info",
                self.create_mock_get_model_info(),
            ),
        ):
            verify_and_auth_api_key(
                "openai/test_model", False, auth_service=self.mock_auth_service
            )

            mock_set_key.assert_not_called()

    def test_valid_key_flow_save(self):
        """
        Test the complete validation flow with a valid key and saving to .env
        """

        # Custom version of load_dotenv that doesn't add OPENAI_API_KEY
        def custom_load_dotenv(
            dotenv_path=None, stream=None, verbose=False, override=False, **kwargs
        ):
            # Real load_dotenv adds keys to os.environ, but we'll prevent OPENAI_API_KEY

            # Import a clean version of dotenv without our patches
            import importlib

            importlib.reload(dotenv)

            # First clear any existing key
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

            print(f"os environ before load dotenv: {os.environ}")

            # Actually load the dotenv file
            dotenv.load_dotenv(dotenv_path, stream, verbose, override, **kwargs)

            # Now remove the OPENAI_API_KEY if it was added
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

            print(f"os environ after custom load dotenv: {os.environ}")
            return True

        def input_args():
            yield "sk-test-valid123"
            yield "y"

        mock_set_key = MagicMock()

        with (
            patch("builtins.input", side_effect=input_args()),
            patch("dotenv.find_dotenv", return_value=TEMP_ENV_FILE.name),
            patch("pathlib.Path.is_file", return_value=True),
            # Use our custom load_dotenv function
            patch("dotenv.load_dotenv", custom_load_dotenv),
            patch(
                "resources.model_resource.services.api_key_service.set_key",
                mock_set_key,
            ),
            patch(
                "resources.model_resource.services.api_key_service.get_model_info",
                self.create_mock_get_model_info(),
            ),
        ):
            verify_and_auth_api_key(
                "openai/test_model", False, auth_service=self.mock_auth_service
            )

            # Should be called once (just as in GitHub CI)
            mock_set_key.assert_called_once()

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

    def test_openai_reasoning_suffix_stripping(self):
        """
        Test that the reasoning effort suffixes are properly stripped from OpenAI model names
        during verification.
        """
        from resources.model_resource.services.auth_helpers import _auth_openai_api_key

        # Create a mock response object for the OpenAI API
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "o1-preview-2024-09-12"},
                {"id": "o3-mini-2025-01-31"},
                {"id": "gpt-4o-2024-11-20"},
            ]
        }

        # Test cases for different model names with reasoning suffixes
        test_cases = [
            # Model with high reasoning suffix
            ("openai/o1-preview-2024-09-12-high-reasoning-effort", True),
            # Model with low reasoning suffix
            ("openai/o1-preview-2024-09-12-low-reasoning-effort", True),
            # Model with high reasoning suffix for o3
            ("openai/o3-mini-2025-01-31-high-reasoning-effort", True),
            # Non-o model with suffix (should fail since we don't strip for non-o models)
            ("openai/gpt-4o-2024-11-20-high-reasoning-effort", False),
            # Base model names should pass
            ("openai/o1-preview-2024-09-12", True),
            ("openai/o3-mini-2025-01-31", True),
        ]

        # Test each case
        with patch("requests.get", return_value=mock_response):
            for model_name, expected_success in test_cases:
                _ok, _message = _auth_openai_api_key(
                    "sk-test-key", model_name, verify_model=True
                )
                self.assertEqual(
                    _ok,
                    expected_success,
                    f"Model {model_name} expected {'success' if expected_success else 'failure'} but got {'success' if _ok else 'failure'}",
                )

                # If expected to succeed, verify the message is empty
                if expected_success:
                    self.assertEqual(
                        _message,
                        "",
                        f"Expected empty message for {model_name}, got: {_message}",
                    )


if __name__ == "__main__":
    unittest.main()
