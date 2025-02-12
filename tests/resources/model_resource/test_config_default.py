from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from resources.model_resource.model_resource import ModelResourceConfig


@pytest.fixture
def mock_env():
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": []}

    with (
        patch(
            "resources.model_resource.services.api_key_service.verify_and_auth_api_key",
            return_value=True,
        ),
        patch("builtins.input", return_value="mock_api_key"),
        patch("requests.get", return_value=mock_response),
    ):
        yield


def test_agent_lm_config(mock_env):
    # Test default configuration
    lm_config1 = ModelResourceConfig()
    assert lm_config1.model == "openai/o3-mini-2025-01-14"
    assert lm_config1.max_output_tokens == 4096
    assert lm_config1.use_helm is False

    # Test custom configuration
    lm_config2 = ModelResourceConfig.create(
        model="custom-model", max_output_tokens=10000
    )
    assert lm_config2.model == "custom-model"
    assert lm_config2.max_output_tokens == 10000
    assert lm_config2.use_helm is True

    # Test Claude model configuration
    lm_config3 = ModelResourceConfig.create(model="claude-v1")
    assert lm_config3.model == "claude-v1"
    assert lm_config3.use_helm is True


def test_invalid_model_name(mock_env):
    with pytest.raises(ValueError, match="Model must be specified"):
        ModelResourceConfig.create(model="")


def test_invalid_max_tokens(mock_env):
    with pytest.raises(
        TypeError, match="'<=' not supported between instances of 'str' and 'int'"
    ):
        ModelResourceConfig.create(model="test-model", max_output_tokens="1000")

    for invalid_token in [-100, 0]:
        with pytest.raises(ValueError, match="max_output_tokens must be positive"):
            ModelResourceConfig.create(
                model="test-model", max_output_tokens=invalid_token
            )
