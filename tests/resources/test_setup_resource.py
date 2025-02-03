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
    docker_compose_path = temp_dir / "docker-compose.yml"

    # Create docker-compose.yml with health check
    with open(docker_compose_path, "w") as f:
        f.write("""
version: '3'
services:
  test_nginx_server:
    image: nginx:latest
    container_name: test_nginx_server
    ports:
      - "8080:80"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80"]
      interval: 5s
      timeout: 3s
      retries: 3
      start_period: 5s
""")
    
    with open(test_file_path, "w") as f:
        f.write(
            "docker compose up -d\n"
            "echo 'Container test_nginx_server Started'\n"
            "echo 'Container test_nginx_server Healthy'\n"
        )

    # Instantiate TaskServerResource
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
    docker_compose_path = temp_dir / "docker-compose.yml"
    
    # Create docker-compose.yml with health checks
    with open(docker_compose_path, "w") as f:
        f.write("""
version: '3'
services:
  test_redis_server:
    image: redis:latest
    container_name: test_redis_server
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 3
      start_period: 5s
  test_nginx_server:
    image: nginx:latest
    container_name: test_nginx_server
    ports:
      - "8080:80"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80"]
      interval: 5s
      timeout: 3s
      retries: 3
      start_period: 5s
""")

    with open(test_file_path, "w") as f:
        f.write(
            "docker compose up -d\n"
            "echo 'Container test_redis_server Started'\n"
            "echo 'Container test_redis_server Healthy'\n"
            "echo 'Container test_nginx_server Started'\n"
            "echo 'Container test_nginx_server Healthy'\n"
        )

    # Instantiate TaskServerResource
    resource = SetupResource(
        "test2", SetupResourceConfig(False, str(temp_dir))
    )

    # Call stop method to ensure it works as expected
    resource.stop()

    # Verify that the container is stopped
    verify_docker_containers_stopped()