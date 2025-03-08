import unittest
from unittest.mock import patch, MagicMock
from resources.model_resource.model_resource import ModelResource, ModelResourceConfig


class TestModelResource(unittest.TestCase):

    @patch('resources.model_resource.services.api_key_service.verify_and_auth_api_key', return_value=None)
    @patch.object(ModelResourceConfig, 'validate', return_value=None)
    @patch.object(ModelResource, 'get_model_provider')
    def setUp(self, mock_get_model_provider, mock_validate, mock_verify):
        mock_get_model_provider.return_value = MagicMock(name='MockModelProvider')
        
        self.config = ModelResourceConfig(
            model="openai/o3-mini-2025-01-14",
            max_output_tokens=4096,
            max_input_tokens=8192,
            max_iterations_stored_in_memory=3,
            use_helm=False,
            temperature=0.5,
            stop_sequences=["STOP_TOKEN"],
            use_mock_model=False
        )
        # Set up the resource
        self.resource = ModelResource(resource_id="test_resource", config=self.config)
        self.resource.total_input_tokens = 0
        self.resource.total_output_tokens = 0

    @patch('resources.model_resource.services.api_key_service.verify_and_auth_api_key', return_value=None)
    @patch.object(ModelResourceConfig, 'validate', return_value=None)
    @patch.object(ModelResource, 'get_model_provider')
    def test_to_dict(self, mock_get_model_provider, mock_validate, mock_verify):
        mock_get_model_provider.return_value = MagicMock(name='MockModelProvider')
        
        expected_dict = {
            "resource_id": "test_resource",
            "config": {
                "model": "openai/o3-mini-2025-01-14",
                "max_output_tokens": 4096,
                "max_input_tokens": 8192,
                "max_iterations_stored_in_memory": 3,
                "helm": False,
                "temperature": 0.5,
                "stop_sequences": ["STOP_TOKEN"],
                "use_mock_model": False,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
            }
        }
        self.assertDictEqual(self.resource.to_dict(), expected_dict)

    @patch('resources.model_resource.services.api_key_service.verify_and_auth_api_key', return_value=None)
    @patch.object(ModelResourceConfig, 'validate', return_value=None)
    @patch.object(ModelResource, 'get_model_provider')
    def test_to_dict_with_mock_model(self, mock_get_model_provider, mock_validate, mock_verify):
        mock_get_model_provider.return_value = MagicMock(name='MockModelProvider')
        
        config = ModelResourceConfig(
            model="openai/o3-mini-2025-01-14",
            max_output_tokens=4096,
            max_input_tokens=8192,
            max_iterations_stored_in_memory=3,
            use_helm=False,
            temperature=0.5,
            stop_sequences=["STOP_TOKEN"],
            use_mock_model=True
        )
        resource = ModelResource(resource_id="test_resource", config=config)
        
        expected_dict = {
            "resource_id": "test_resource",
            "config": {
                "use_mock_model": True
            }
        }
        self.assertDictEqual(resource.to_dict(), expected_dict)


if __name__ == '__main__':
    unittest.main()