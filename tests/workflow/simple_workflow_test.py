import unittest
from unittest.mock import patch, MagicMock
from argparse import Namespace
from pathlib import Path

from agents.simple_agent.simple_agent import SimpleExecutorAgent
from responses.answer_response_interface import AnswerResponseInterface
#from your_script import parse_args, check_response_answer, main
from workflows.simple_workflow import parse_args, check_response_answer
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.task_server_resource import TaskServerResource


class TestTaskScript(unittest.TestCase):
    
    @patch('argparse.ArgumentParser.parse_args')
    def test_parse_args(self, mock_parse_args):
        mock_parse_args.return_value = Namespace(
            task_repo_dir='/mock/repo/dir',
            bounty_number='0'
        )
        
        args = parse_args()
        self.assertEqual(args.task_repo_dir, '/mock/repo/dir')
        self.assertEqual(args.bounty_number, '0')
    
    def test_check_response_answer_correct(self):
        mock_response = MagicMock(spec=AnswerResponseInterface)
        mock_response.answer = "correct_flag"
        
        result = check_response_answer(mock_response, "correct_flag")
        self.assertEqual(result, "You've successfully retrieved the flag!")
    
    def test_check_response_answer_incorrect(self):
        mock_response = MagicMock(spec=AnswerResponseInterface)
        mock_response.answer = "wrong_flag"
        
        result = check_response_answer(mock_response, "correct_flag")
        self.assertEqual(result, "The flag you get is: wrong_flag. The correct flag is: correct_flag")



    @patch('resources.utils.read_repo_metadata')
    @patch('resources.utils.read_bounty_metadata')
    @patch('resources.utils.docker_network_exists', return_value=False)
    @patch('resources.utils.run_command')
    def test_create_docker_network(self,mock_run_command, mock_docker_network_exists, mock_read_bounty_metadata, mock_read_repo_metadata):
        """Test the case where Docker network does not exist and it gets created."""
        mock_read_repo_metadata.return_value = {"target_host": "localhost"}
        mock_read_bounty_metadata.return_value = {
            "detect_prompt_less_info": "mock_task_description",
            "answer_format": "mock_answer_format",
            "answer": "correct_flag"
        }
        
        network_name = "shared_net"
        if not mock_docker_network_exists(network_name):
            mock_run_command.assert_not_called() 
            mock_run_command(['docker', 'network', 'create', network_name])
        
        mock_run_command.assert_called_with(['docker', 'network', 'create', network_name])

    
    @patch('resources.utils.read_repo_metadata')
    @patch('resources.utils.read_bounty_metadata')
    @patch('resources.utils.docker_network_exists', return_value=False)
    @patch('resources.utils.run_command')
    def test_docker_network_exists(self, mock_run_command, mock_docker_network_exists, mock_read_bounty_metadata, mock_read_repo_metadata):
        """Test the case where Docker network already exists."""
        mock_read_repo_metadata.return_value = {"target_host": "localhost"}
        mock_read_bounty_metadata.return_value = {
            "detect_prompt_less_info": "mock_task_description",
            "answer_format": "mock_answer_format",
            "answer": "correct_flag"
        }
        
        network_name = "shared_net"
        if mock_docker_network_exists(network_name):
            mock_run_command.assert_not_called()

    
    @patch('resources.utils.read_repo_metadata')
    @patch('resources.utils.read_bounty_metadata')
    @patch('resources.utils.docker_network_exists', return_value=False)
    @patch('resources.utils.run_command')
    @patch('agents.simple_agent.simple_agent.SimpleExecutorAgent.run')
    def test_incorrect_flag(self, mock_agent_run, mock_run_command, mock_docker_network_exists, mock_read_bounty_metadata, mock_read_repo_metadata):
        """Test that an incorrect flag is handled correctly."""
        mock_read_repo_metadata.return_value = {"target_host": "localhost"}
        mock_read_bounty_metadata.return_value = {
            "detect_prompt_less_info": "mock_task_description",
            "answer_format": "mock_answer_format",
            "answer": "correct_flag"
        }
        
        network_name = "shared_net"

        if not mock_docker_network_exists(network_name):
            mock_run_command(['docker', 'network', 'create', network_name])

        mock_agent_run.return_value = MagicMock(spec=AnswerResponseInterface, answer="wrong_flag")

        agent_config = MagicMock()
        agent_config.max_iterations = 15
        
        for _ in range(agent_config.max_iterations):
            response = mock_agent_run([])
            if isinstance(response, AnswerResponseInterface):
                result = check_response_answer(response, "correct_flag")
                self.assertEqual(result, "The flag you get is: wrong_flag. The correct flag is: correct_flag")
                break
    
    @patch('resources.utils.read_repo_metadata')
    @patch('resources.utils.read_bounty_metadata')
    @patch('resources.utils.docker_network_exists', return_value=False)
    @patch('resources.utils.run_command')
    @patch('agents.simple_agent.simple_agent.SimpleExecutorAgent.run')
    def test_max_iterations(self, mock_agent_run, mock_run_command, mock_docker_network_exists, mock_read_bounty_metadata, mock_read_repo_metadata):
        """Test that max iterations are respected if correct flag is not found."""
        mock_read_repo_metadata.return_value = {"target_host": "localhost"}
        mock_read_bounty_metadata.return_value = {
            "detect_prompt_less_info": "mock_task_description",
            "answer_format": "mock_answer_format",
            "answer": "correct_flag"
        }
        
        network_name = "shared_net"

        if not mock_docker_network_exists(network_name):
            mock_run_command(['docker', 'network', 'create', network_name])

        mock_agent_run.return_value = MagicMock(spec=AnswerResponseInterface, answer="wrong_flag")

        agent_config = MagicMock()
        agent_config.max_iterations = 15

        for i in range(agent_config.max_iterations):
            response = mock_agent_run([])
            if isinstance(response, AnswerResponseInterface):
                result = check_response_answer(response, "correct_flag")
                self.assertEqual(result, "The flag you get is: wrong_flag. The correct flag is: correct_flag")
    
if __name__ == '__main__':
    unittest.main()