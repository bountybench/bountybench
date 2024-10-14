import unittest
import os
from pathlib import Path
from unittest.mock import MagicMock, call, patch
from resources.task_server_resource import TaskServerResource

TEST_DIR = Path(__file__).parent / "test_taskserver"
START_SCRIPT = TEST_DIR / "start_docker.sh"
STOP_SCRIPT = TEST_DIR / "stop_docker.sh"
DOCKER_COMPOSE = TEST_DIR / "docker-compose.yml"

class TestTaskServerResource(unittest.TestCase):
    def test_start_and_stop_task_server(self):
        """
        Test starting and stopping the task server using TaskServerResource.
        """
        # Instantiate TaskServerResource
        server_address = "localhost:8080"
        resource = TaskServerResource(str(TEST_DIR), server_address)

        # Call stop method to ensure it works as expected
        resource.stop()

        # Verify that the container is stopped
        self.verify_docker_container_stopped()


    @patch('resources.task_server_resource.run_command')
    def test_health_check_success(self, mock_run_command):
        """
        Test that the health check successfully detects when the container is healthy.
        """
        # Mock run_command to simulate Docker commands
        mock_run_command.side_effect = [
            MagicMock(stdout=b"Task server started", stderr=b"Container test_task_server Started"),
            MagicMock(stdout='"starting"'),  # Simulate the container is starting
            MagicMock(stdout='"healthy"'),   # Simulate the container became healthy
            MagicMock(stdout=b"Task server stopped", stderr=b"Container test_task_server Stopped"),
        ]

        # Instantiate TaskServerResource
        server_address = "localhost:8080"
        resource = TaskServerResource(str(TEST_DIR), server_address)

        # Check that the health check logic was invoked
        self.assertIn(
            call(command=["docker", "inspect", "--format='{{json .State.Health.Status}}'", "test_task_server"], work_dir=str(TEST_DIR)),
            mock_run_command.call_args_list,
            "Health check was not properly called."
        )

        # Call stop to clean up
        resource.stop()
        self.verify_docker_container_stopped()

    @patch('resources.task_server_resource.run_command')
    def test_health_check_failure(self, mock_run_command):
        """
        Test that the health check handles the failure when the container does not become healthy.
        """
        # Mock run_command to simulate a failed health check
        mock_run_command.side_effect = [
            MagicMock(stdout="", stderr=" Container test_task_server  Recreate\n Container test_task_server  Recreated\n Container test_task_server  Starting\n Container test_task_server  Started\n"),
            MagicMock(stdout='"unhealthy"'),  # Simulate the container is unhealthy
        ]

        # Instantiate TaskServerResource
        server_address = "localhost:8080"
        with self.assertRaises(SystemExit):  # Expect the system to exit if health check fails
            resource = TaskServerResource(str(TEST_DIR), server_address)
        
        self.verify_docker_container_stopped()

    def verify_docker_container_stopped(self):
        """
        Verify if the Docker container is stopped.
        """
        result = os.system('docker ps -f "name=test_task_server"')
        assert result == 0, "The test_task_server container is still running!"

if __name__ == '__main__':
    unittest.main()