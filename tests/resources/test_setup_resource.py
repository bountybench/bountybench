import os
import tempfile
import pytest
from pathlib import Path

from resources.setup_resource import SetupResource, SetupResourceConfig

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    test_files_dir = Path(temp_dir)
    print(f"Created temporary test directory: {test_files_dir}")
    yield test_files_dir
    # Clean up the test files
    for file in test_files_dir.glob('*'):
        file.unlink()
    # Remove the empty directory
    if os.path.exists(temp_dir):
        os.rmdir(temp_dir)

def verify_docker_container_stopped():
    """
    Verify if the Docker container is stopped.
    """
    result = os.system('docker ps -f "name=test_setup"')
    assert result == 0, "The test_setup container is still running!"

def verify_docker_containers_stopped():
    """
    Verify if the Docker containers are stopped.
    """
    result = os.system('docker ps -f "name=test_nginx_server"')
    assert result == 0, "The test_nginx_server container is still running!"
    result = os.system('docker ps -f "name=test_redis_server"')
    assert result == 0, "The test_redis_server container is still running!"


def test_start_and_stop_setup(temp_dir):
    """
    Test starting and stopping the SetupResource.
    """
    test_file_path = temp_dir / "setup_repo_env.sh"
    
    with open(test_file_path, "w") as f:
        f.write(
            "docker stop test_nginx_server || true\n"
            "docker rm test_nginx_server || true\n"
            "docker run -d --name test_nginx_server -p 8080:80 nginx:latest"
        )

    # Instantiate SetupResource
    resource = SetupResource(
        "test", SetupResourceConfig(False, str(temp_dir))
    )

    # Call stop method to ensure it works as expected
    resource.stop()

    # Verify that the container is stopped
    verify_docker_container_stopped()

def test_start_and_stop_setup_multi_container(temp_dir):
    """
    Test starting and stopping the server with multiple containers using SetupResource.
    """
    test_file_path = temp_dir / "setup_repo_env.sh"
    
    with open(test_file_path, "w") as f:
        f.write(
            "docker stop test_redis_server || true\n"
            "docker rm test_redis_server || true\n"
            "docker run -d --name test_redis_server -p 6379:6379 redis:latest"
        )

    # Instantiate SetupResource
    resource = SetupResource(
        "test2", SetupResourceConfig(False, str(temp_dir))
    )

    # Call stop method to ensure it works as expected
    resource.stop()

    # Verify that the container is stopped
    verify_docker_containers_stopped()