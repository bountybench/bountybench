import unittest
from unittest.mock import patch
from agents.executor_agent.executor_agent import ExecutorAgent    
from models.query import query
from agents.prompts import STOP_TOKEN

from resources.model_resource.model_response import ModelResponse
from agents.dataclasses.agent_spec import AgentConfig
from resources.kali_env_resource import KaliEnvResource


from unittest.mock import patch, MagicMock


# Initialize KaliEnvResource for the testing instance
kali_env = KaliEnvResource(name=f"kali-env", volumes=None)

class TestHandleRequest(unittest.TestCase):

    def setUp(self):
        self.config = AgentConfig(
            model="openai/o1-mini-2024-09-12",
            max_output_tokens=50,
            max_input_tokens=100,
            max_iterations=3,
            max_iterations_stored_in_memory=3,
            use_helm=True
        )
        self.agent = ExecutorAgent(config=self.config)

    @patch('agents.executor_agent.executor_agent.query')  
    def test_handle_request_with_o1_model(self, mock_query):
        mock_model_response = MagicMock(spec=ModelResponse)
        mock_model_response.content = "Test response"
        mock_query.return_value = mock_model_response

        self.agent.config.model = "openai/o1-mini-2024-09-12"
        self.agent.config.max_output_tokens = 100
        self.agent.config.use_helm = True

        response = self.agent._handle_request("Test input")

        mock_query.assert_called_once_with(
            model="openai/o1-mini-2024-09-12",
            message="Test input",
            temperature=1,  
            max_tokens=100,
            stop_sequences=[],
            helm=True
        )
        
        mock_model_response.remove_hallucinations.assert_called_once()
        self.assertEqual(response, "Test response\n<END>")

    
    @patch('agents.executor_agent.executor_agent.query')  
    def test_handle_request_with_non_o1_model(self, mock_query):
        """ Test with a model without 'o1' in its name. """
        mock_model_response = MagicMock(spec=ModelResponse)
        mock_model_response.content = "Second response"
        mock_query.return_value = mock_model_response

        self.agent.config.model = "anthropic/claude-3-5-sonnet-20240620"
        self.agent.config.max_output_tokens = 150
        self.agent.config.use_helm = True

        response = self.agent._handle_request("Second input")

        mock_query.assert_called_once_with(
            model="anthropic/claude-3-5-sonnet-20240620",
            message="Second input",
            temperature=0.5, 
            max_tokens=150,
            stop_sequences=[STOP_TOKEN],
            helm=True
        )
        mock_model_response.remove_hallucinations.assert_called_once()
        self.assertEqual(response, "Second response\n<END>")

    @patch('agents.executor_agent.executor_agent.query')  
    def test_handle_request_empty_response(self, mock_query):
        """ Test when the query returns an empty response. """
        mock_model_response = MagicMock(spec=ModelResponse)
        mock_model_response.content = ""  
        mock_query.return_value = mock_model_response

        response = self.agent._handle_request("Input with empty response")

        mock_query.assert_called_once()
        mock_model_response.remove_hallucinations.assert_called_once()
        self.assertEqual(response, "\n<END>")  

if __name__ == '__main__':
    unittest.main()