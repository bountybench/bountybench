import unittest
from unittest.mock import patch, MagicMock
import os
from docker.errors import NotFound
from pathlib import Path
from resources.docker_resource import DockerResourceConfig, DockerResource

class TestDockerResource(unittest.TestCase):
    def setUp(self):
        # Mock Docker configuration and resource
        self.resource_id = "test_resource"
        self.config = DockerResourceConfig()
        self.docker_resource = DockerResource(self.resource_id, self.config)
    
    @patch("docker.from_env")
    def test_execute_creates_tmp_file(self, mock_docker_from_env):
        """Test if /tmp/poc.txt is created inside the container"""
        # Mock Docker container and its methods
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_docker_from_env.return_value = mock_client
        mock_client.containers.run.return_value = mock_container
        
        # Mock container logs and result
        mock_container.logs.return_value = iter([b"Exploit successful\n"])
        mock_container.wait.return_value = {"StatusCode": 0}
        
        # Define a test command that creates /tmp/poc.txt
        docker_image = "cybench/cybounty:latest"
        command = 'echo "Exploit successful" > /tmp/poc.txt'
        
        # Execute the command
        logs, exit_code = self.docker_resource.execute(
            docker_image=docker_image,
            network="shared_net",
            command=command
        )
        
        # Assertions
        self.assertEqual(exit_code, 0)
        self.assertIn("Exploit successful", logs)
        
        # Ensure container methods were called
        mock_client.containers.run.assert_called_once()
        mock_container.logs.assert_called()
        mock_container.wait.assert_called_once()
        mock_container.remove.assert_called_once_with(force=True)
        
        # Ensure the container's /tmp/poc.txt is not accessible on the host
        self.assertFalse(Path("/tmp/poc.txt").exists(), "Host /tmp/poc.txt should not exist.")

    @patch("docker.from_env")
    def test_cleanup_on_failure(self, mock_docker_from_env):
        """Test if the container is cleaned up properly on failure"""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_docker_from_env.return_value = mock_client
        mock_client.containers.run.side_effect = Exception("Simulated error")
        
        # Define a test command
        docker_image = "cybench/cybounty:latest"
        command = "invalid command"
        
        # Execute the command and expect failure
        logs, exit_code = self.docker_resource.execute(
            docker_image=docker_image,
            network="shared_net",            
            command=command
        )
        
        # Assertions
        self.assertNotEqual(exit_code, 0)
        self.assertIn("Simulated error", logs)
        
        # Ensure cleanup was attempted
        mock_client.containers.run.assert_called_once()
        mock_container.remove.assert_not_called()  # Shouldn't be called as container didn't start

if __name__ == "__main__":
    unittest.main()