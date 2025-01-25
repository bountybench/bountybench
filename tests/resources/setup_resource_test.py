import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from resources.setup_resource import SetupResource, SetupResourceConfig

TEST_DIR = Path(__file__).parent / "test_taskserver"
TEST_DIR2 = Path(__file__).parent / "test_taskserver2"


class TestTaskServerResource(unittest.TestCase):
    def test_start_and_stop_setup(self):
        """
        Test starting and stopping the SetupResource.
        """
        # Instantiate TaskServerResource
        resource = SetupResource("test", SetupResourceConfig(False, str(TEST_DIR)))

        # Call stop method to ensure it works as expected
        resource.stop()

        # Verify that the container is stopped
        self.verify_docker_container_stopped()

    def test_start_and_stop_setup_multi_container(self):
        """
        Test starting and stopping the server with multiple containers using SetupResource.
        """
        # Instantiate SetupResource
        resource = SetupResource("test2", SetupResourceConfig(False, str(TEST_DIR)))

        # Call stop method to ensure it works as expected
        resource.stop()

        # Verify that the container is stopped
        self.verify_docker_containers_stopped()

    def verify_docker_container_stopped(self):
        """
        Verify if the Docker container is stopped.
        """
        result = os.system('docker ps -f "name=test_setup"')
        assert result == 0, "The test_setup container is still running!"

    def verify_docker_containers_stopped(self):
        """
        Verify if the Docker containers is stopped.
        """
        result = os.system('docker ps -f "name=test_nginx_server"')
        assert result == 0, "The test_nginx_server container is still running!"
        result = os.system('docker ps -f "name=test_redis_server"')
        assert result == 0, "The test_redis_server container is still running!"


if __name__ == "__main__":
    unittest.main()
