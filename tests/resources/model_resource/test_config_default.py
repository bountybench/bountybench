import pytest
from unittest.mock import patch, Mock
import requests
from pathlib import Path
from resources.model_resource.model_resource import ModelResourceConfig

def test_agent_lm_config():
    # Mock API key verification and network requests
    def mock_requests_get(*args, **kwargs):
        mock_response = requests.Response()
        mock_response.status_code = 200
        mock_response.json = lambda: {}  # Return empty JSON
        return mock_response

    mock_path = Mock(spec=Path)
    mock_path.is_file.return_value = True

    # Isolate configuration testing with additional mocks
    with patch('resources.model_resource.services.api_key_service.verify_and_auth_api_key', return_value=True), \
         patch('builtins.input', return_value='mock_api_key'), \
         patch('os.environ.get', return_value='mock_api_key'), \
         patch('requests.get', side_effect=mock_requests_get), \
         patch('resources.model_resource.services.api_key_service.find_dotenv', return_value='/fake/path/.env'), \
         patch('resources.model_resource.services.api_key_service.Path', return_value=mock_path), \
         patch('resources.model_resource.services.api_key_service.load_dotenv'):

        # Test default configuration
        lm_config1 = ModelResourceConfig()
        assert lm_config1.model == "openai/o3-mini-2025-01-14"
        assert lm_config1.max_output_tokens == 4096
        assert lm_config1.use_helm is False

        # Test custom configuration
        lm_config2 = ModelResourceConfig.create(
            model="custom-model", 
            max_output_tokens=10000
        )
        assert lm_config2.model == "custom-model"
        assert lm_config2.max_output_tokens == 10000
        assert lm_config2.use_helm is True

        # Test Claude model configuration
        lm_config3 = ModelResourceConfig.create(model="claude-v1")
        assert lm_config3.model == "claude-v1"
        assert lm_config3.use_helm is True