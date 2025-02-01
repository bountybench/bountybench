import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from resources.setup_resource import SetupResource, SetupResourceConfig


class TestTaskServerResource(unittest.TestCase):
    def test_start_and_stop_setup(self):
        """
        Test starting and stopping the SetupResource.
        """
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        test_files_dir = Path(temp_dir)
        print(f"Created temporary test directory: {test_files_dir}")

        test_file_path = test_files_dir / "setup_repo_env.sh"
        with open(test_file_path, "w") as f:
            f.write(
                "docker stop test_nginx_server || true\ndocker rm test_nginx_server || true\ndocker run -d --name test_nginx_server -p 8080:80 nginx:latest"
            )

        # Instantiate TaskServerResource
        resource = SetupResource(
            "test", SetupResourceConfig(False, str(test_files_dir))
        )

        # Call stop method to ensure it works as expected
        resource.stop()

        # Verify that the container is stopped
        self.verify_docker_container_stopped()

    def test_start_and_stop_setup_multi_container(self):
        """
        Test starting and stopping the server with multiple containers using SetupResource.
        """
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        test_files_dir = Path(temp_dir)
        print(f"Created temporary test directory: {test_files_dir}")

        test_file_path = test_files_dir / "setup_repo_env.sh"
        with open(test_file_path, "w") as f:
            f.write(
                "docker stop test_redis_server || true\ndocker rm test_redis_server || true\ndocker run -d --name test_redis_server -p 6379:6379 redis:latest"
            )

        # Instantiate TaskServerResource
        resource = SetupResource(
            "test2", SetupResourceConfig(False, str(test_files_dir))
        )

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
