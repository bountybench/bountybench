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
        patch("pathlib.Path.is_file", return_value=True),
        patch("dotenv.load_dotenv", return_value=True),
        patch(
            "resources.model_resource.services.api_key_service.verify_and_auth_api_key",
            return_value=True,
        ),
        patch("builtins.input", return_value="mock_api_key"),
        patch("requests.get", return_value=mock_response),
    ):
        yield


def test_agent_lm_config(mock_env):
    lm_config1 = ModelResourceConfig()
    assert lm_config1.model == "openai/o3-mini-2025-01-14"
    assert lm_config1.max_output_tokens == 4096
    assert lm_config1.use_helm is False

    lm_config2 = ModelResourceConfig(model="custom-model", max_output_tokens=10000)
    assert lm_config2.model == "custom-model"
    assert lm_config2.max_output_tokens == 10000
    assert lm_config2.use_helm is True


def test_invalid_model_name(mock_env):
    with pytest.raises(ValueError, match="Model must be specified"):
        ModelResourceConfig(model="")


def test_invalid_max_tokens(mock_env):
    with pytest.raises(ValueError, match="max_output_tokens must be positive"):
        ModelResourceConfig(model="test-model", max_output_tokens=0)

    with pytest.raises(ValueError, match="max_output_tokens must be positive"):
        ModelResourceConfig(model="test-model", max_output_tokens=-100)
