import unittest
import os
from pathlib import Path
from unittest.mock import MagicMock, call, patch
from resources.task_server_resource import TaskServerResource

TEST_DIR = Path(__file__).parent / "test_taskserver"
TEST_DIR2 = Path(__file__).parent / "test_taskserver2"

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

    def test_start_and_stop_task_server_multi_container(self):
        """
        Test starting and stopping the task server with multiple containers using TaskServerResource.
        """
        # Instantiate TaskServerResource
        server_address = "localhost:8080"
        resource = TaskServerResource(str(TEST_DIR2), server_address)

        # Call stop method to ensure it works as expected
        resource.stop()

        # Verify that the container is stopped
        self.verify_docker_containers_stopped()

    def verify_docker_container_stopped(self):
        """
        Verify if the Docker container is stopped.
        """
        result = os.system('docker ps -f "name=test_task_server"')
        assert result == 0, "The test_task_server container is still running!"

    def verify_docker_containers_stopped(self):
        """
        Verify if the Docker containers is stopped.
        """
        result = os.system('docker ps -f "name=test_nginx_server"')
        assert result == 0, "The test_nginx_server container is still running!"
        result = os.system('docker ps -f "name=test_redis_server"')
        assert result == 0, "The test_redis_server container is still running!"
if __name__ == '__main__':
    unittest.main()