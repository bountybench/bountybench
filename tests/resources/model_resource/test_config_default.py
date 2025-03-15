from pathlib import Path
from unittest.mock import Mock, patch
import sys

import pytest

from resources.model_resource.model_resource import ModelResourceConfig

module = sys.modules[ModelResourceConfig.__module__]


@pytest.fixture
def mock_env():
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": []}

    # Different mocks to account for different model providers & JSON responses
    openai_mock = Mock()
    openai_mock.status_code = 200
    openai_mock.json.return_value = {"data": [{"id": "gpt-4o"}]}

    anthropic_mock = Mock()
    anthropic_mock.status_code = 200
    anthropic_mock.json.return_value = {"data": [{"id": "claude-3-opus"}]}

    helm_mock = Mock()
    helm_mock.status_code = 200
    helm_mock.json.return_value = {"all_models": [{"name": "anthropic/claude-3-opus"}]}

    def get_mock_response(url, *args, **kwargs):
        if "openai" in url:
            return openai_mock
        elif "anthropic" in url:
            return anthropic_mock
        elif "crfm-models" in url:
            return helm_mock
        return mock_response

    with (
        patch("pathlib.Path.is_file", return_value=True),
        patch("dotenv.load_dotenv", return_value=True),
        patch.object(
            module, "verify_and_auth_api_key", return_value=True
        ),  # We need to patch where the object is looked up, not where it is defined
        patch("builtins.input", return_value="mock_api_key"),
        patch("requests.get", side_effect=get_mock_response),
    ):
        yield


def test_agent_lm_config(mock_env):
    # Test with explicitly specified OpenAI model
    lm_config1 = ModelResourceConfig(model="openai/gpt-4o")
    assert lm_config1.model == "openai/gpt-4o"
    assert lm_config1.max_output_tokens == 4096
    assert lm_config1.use_helm is False

    # Test with custom output tokens
    lm_config2 = ModelResourceConfig(model="openai/gpt-4o", max_output_tokens=10000)
    assert lm_config2.model == "openai/gpt-4o"
    assert lm_config2.max_output_tokens == 10000
    assert lm_config2.use_helm is False

    # Test with an Anthropic model
    lm_config3 = ModelResourceConfig(model="anthropic/claude-3-opus", use_helm=False)
    assert lm_config3.model == "anthropic/claude-3-opus"
    assert lm_config3.use_helm is False

    # Explicitly setting use_helm to True
    lm_config4 = ModelResourceConfig(model="anthropic/claude-3-opus", use_helm=True)
    assert lm_config4.model == "anthropic/claude-3-opus"
    assert lm_config4.use_helm is True

    # Set some fields, then make a copy with a different model name
    lm_config5 = ModelResourceConfig(
        model="anthropic/claude-3-opus",
        max_input_tokens=10000,
        temperature=0.7,
        use_helm=True,
    )
    assert lm_config5.model == "anthropic/claude-3-opus"
    lm_config5_copy = lm_config5.copy_with_changes(model="openai/gpt-4o")
    assert lm_config5_copy.model == "openai/gpt-4o"
    assert lm_config5_copy.max_input_tokens == 10000
    assert lm_config5_copy.temperature == 0.7
    assert lm_config5_copy.use_helm is True


def test_invalid_model_name(mock_env):
    with pytest.raises(ValueError, match="Model must be specified"):
        ModelResourceConfig(model="")

    # Test that default constructor without model specified raises exception
    with pytest.raises(Exception):
        ModelResourceConfig()


def test_invalid_max_tokens(mock_env):
    with pytest.raises(ValueError, match="max_output_tokens must be positive"):
        ModelResourceConfig(model="test-model", max_output_tokens=0)

    with pytest.raises(ValueError, match="max_output_tokens must be positive"):
        ModelResourceConfig(model="test-model", max_output_tokens=-100)
