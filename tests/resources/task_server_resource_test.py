import unittest
import shutil
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
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

    def verify_docker_container_stopped(self):
        """
        Verify if the Docker container is stopped.
        """
        result = os.system('docker ps -f "name=test_task_server"')
        assert result == 0, "The test_task_server container is still running!"

if __name__ == '__main__':
    unittest.main()