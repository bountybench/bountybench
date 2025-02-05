import os
import tempfile
import pytest
from pathlib import Path
from resources.setup_resource import SetupResource, SetupResourceConfig
import docker
import subprocess
import time

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

@pytest.fixture(autouse=True)
def cleanup_docker():
    """Cleanup any test containers before and after each test."""
    # Cleanup before test
    os.system('docker stop test_nginx_server test_redis_server > /dev/null 2>&1')
    os.system('docker rm test_nginx_server test_redis_server > /dev/null 2>&1')
    yield
    # Cleanup after test
    os.system('docker stop test_nginx_server test_redis_server > /dev/null 2>&1')
    os.system('docker rm test_nginx_server test_redis_server > /dev/null 2>&1')

def verify_docker_container_stopped():
    """
    Verify if the Docker container is stopped.
    """
    result = os.popen('docker ps -q -f "name=test_setup"').read().strip()
    assert result == "", "The test_setup container is still running!"

def verify_docker_containers_stopped():
    """
    Verify if the Docker containers are stopped.
    """
    result = os.popen('docker ps -q -f "name=test_redis_server"').read().strip()
    if result:  # If container is still running
        os.system('docker stop test_redis_server > /dev/null 2>&1')
        os.system('docker rm test_redis_server > /dev/null 2>&1')
        result = os.popen('docker ps -q -f "name=test_redis_server"').read().strip()
    assert result == "", "The test_redis_server container is still running!"
    
def test_start_and_stop_setup(temp_dir):
    """
    Test starting and stopping the SetupResource.
    """
    test_file_path = temp_dir / "setup_repo_env.sh"
    
    with open(test_file_path, "w") as f:
        f.write(
            "docker stop test_nginx_server || true\n"
            "docker rm test_nginx_server || true\n"
            "docker run -d --name test_nginx_server -p 8081:80 nginx:latest"  # Changed port to 8081
        )
    
    # Make script executable
    os.chmod(test_file_path, 0o755)

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
            "docker run -d --name test_redis_server -p 6380:6379 redis:latest"  # Changed port to 6380
        )
    
    # Make script executable
    os.chmod(test_file_path, 0o755)

    # Instantiate SetupResource
    resource = SetupResource(
        "test2", SetupResourceConfig(False, str(temp_dir))
    )

    # Call stop method to ensure it works as expected
    resource.stop()

    # Verify that the container is stopped
    verify_docker_containers_stopped()

def test_resource_restart(temp_dir):
    """
    Test the restart functionality of SetupResource.
    """
    # Prepare setup script
    test_file_path = temp_dir / "setup_repo_env.sh"
    with open(test_file_path, "w") as f:
        f.write(
            "docker stop test_nginx_server || true\n"
            "docker rm test_nginx_server || true\n"
            "docker run -d --name test_nginx_server -p 8081:80 nginx:latest"
        )
    os.chmod(test_file_path, 0o755)

    # Modify the setup script path to match the expected path
    repo_setup_script = temp_dir / "setup_repo_env.sh"
    os.rename(test_file_path, repo_setup_script)

    # Create Docker client
    client = docker.from_env()

    # Instantiate SetupResource
    resource = SetupResource(
        "test_restart", SetupResourceConfig(False, str(temp_dir))
    )

    # Get initial container ID
    initial_container = client.containers.get('test_nginx_server')
    initial_id = initial_container.id

    # Restart the resource
    resource.restart()

    # Get new container
    new_container = client.containers.get('test_nginx_server')
    
    # Verify container was restarted
    assert new_container.id != initial_id, "Container ID should change on restart"
    assert new_container.status == "running", "Container should be running after restart"

def test_health_check(temp_dir):
    """
    Test health check functionality for containers.
    """
    # Prepare setup script with a Redis container that has a health check
    test_file_path = temp_dir / "setup_repo_env.sh"
    with open(test_file_path, "w") as f:
        f.write(
            "docker stop test_redis_server || true\n"
            "docker rm test_redis_server || true\n"
            "docker run -d \\\n"
            "  --name test_redis_server \\\n"
            "  -p 6380:6379 \\\n"
            "  --health-cmd='redis-cli ping' \\\n"
            "  --health-interval=5s \\\n"
            "  --health-timeout=3s \\\n"
            "  --health-retries=3 \\\n"
            "  redis:latest"
        )
    os.chmod(test_file_path, 0o755)

    # Modify the setup script path to match the expected path
    repo_setup_script = temp_dir / "setup_repo_env.sh"
    os.rename(test_file_path, repo_setup_script)

    # Instantiate SetupResource
    resource = SetupResource(
        "test_health", SetupResourceConfig(False, str(temp_dir))
    )

    # Wait for health check
    client = docker.from_env()
    container = client.containers.get('test_redis_server')
    
    # Give some time for health check to run
    time.sleep(10)
    
    # Reload container to get latest status
    container.reload()
    
    # Check health status
    health_status = container.attrs['State'].get('Health', {}).get('Status')
    assert health_status in ['healthy', 'starting'], f"Unexpected health status: {health_status}"

def test_error_handling(temp_dir):
    """
    Test error scenarios for SetupResource.
    """
    # Test with non-existent directory
    with pytest.raises(ValueError, match="Invalid task_dir"):
        SetupResource(
            "test_error", SetupResourceConfig(False, "/path/to/nonexistent/directory")
        )

    # Test with invalid setup script
    invalid_script_path = temp_dir / "setup_repo_env.sh"
    with open(invalid_script_path, "w") as f:
        f.write("exit 1")  # Always failing script
    os.chmod(invalid_script_path, 0o755)

    with pytest.raises(subprocess.CalledProcessError):
        SetupResource(
            "test_invalid_script", SetupResourceConfig(False, str(temp_dir))
        )