import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import docker
import pytest

from resources.setup_resource import SetupResource, SetupResourceConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_files_dir = Path(temp_dir)
        print(f"Created temporary test directory: {test_files_dir}")
        yield test_files_dir


@pytest.fixture(autouse=True)
def cleanup_docker():
    """Cleanup any test containers before and after each test."""
    containers = [
        "test_nginx_server",
        "test_redis_server",
        "lunary-app",
        "lunary-postgres",
    ]
    for container in containers:
        subprocess.run(["docker", "stop", container], capture_output=True)
        subprocess.run(["docker", "rm", container], capture_output=True)
    yield
    for container in containers:
        subprocess.run(["docker", "stop", container], capture_output=True)
        subprocess.run(["docker", "rm", container], capture_output=True)


def verify_docker_containers_stopped(*container_names):
    """
    Verify if the specified Docker containers are stopped.
    """
    for container in container_names:
        result = subprocess.run(
            ["docker", "ps", "-q", "-f", f"name={container}"],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip():  # If container is still running
            subprocess.run(["docker", "stop", container], capture_output=True)
            subprocess.run(["docker", "rm", container], capture_output=True)
            result = subprocess.run(
                ["docker", "ps", "-q", "-f", f"name={container}"],
                capture_output=True,
                text=True,
            )
        assert (
            result.stdout.strip() == ""
        ), f"The {container} container is still running!"


def test_start_and_stop_setup(temp_dir):
    """Test starting and stopping the SetupResource with a single container."""
    test_file_path = temp_dir / "setup_repo_env.sh"
    test_file_path.write_text(
        "docker stop test_nginx_server || true\n"
        "docker rm test_nginx_server || true\n"
        "docker run -d --name test_nginx_server -p 8081:80 nginx:latest"
    )
    test_file_path.chmod(0o755)

    resource = SetupResource("test", SetupResourceConfig(False, temp_dir))
    resource.stop()
    verify_docker_containers_stopped("test_nginx_server")


def test_start_and_stop_setup_multi_container(temp_dir):
    """Test starting and stopping multiple containers using SetupResource."""
    test_file_path = temp_dir / "setup_repo_env.sh"
    test_file_path.write_text(
        "docker stop test_redis_server || true\n"
        "docker rm test_redis_server || true\n"
        "docker run -d --name test_redis_server -p 6380:6379 redis:latest"
    )
    test_file_path.chmod(0o755)

    resource = SetupResource("test2", SetupResourceConfig(False, temp_dir))
    resource.stop()
    verify_docker_containers_stopped("test_redis_server")


def test_resource_restart(temp_dir):
    """Test the restart functionality of SetupResource."""
    test_file_path = temp_dir / "setup_repo_env.sh"
    test_file_path.write_text(
        "docker stop test_nginx_server || true\n"
        "docker rm test_nginx_server || true\n"
        "docker run -d --name test_nginx_server -p 8081:80 nginx:latest"
    )
    test_file_path.chmod(0o755)

    client = docker.from_env()
    resource = SetupResource("test_restart", SetupResourceConfig(False, temp_dir))

    initial_container = client.containers.get("test_nginx_server")
    initial_id = initial_container.id

    resource.restart()

    new_container = client.containers.get("test_nginx_server")
    assert new_container.id != initial_id, "Container ID should change on restart"
    assert (
        new_container.status == "running"
    ), "Container should be running after restart"


def test_health_check(temp_dir):
    """Test health check functionality for containers."""
    test_file_path = temp_dir / "setup_repo_env.sh"
    test_file_path.write_text(
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
    test_file_path.chmod(0o755)

    resource = SetupResource("test_health", SetupResourceConfig(False, temp_dir))

    client = docker.from_env()
    container = client.containers.get("test_redis_server")
    time.sleep(10)
    container.reload()

    health_status = container.attrs["State"].get("Health", {}).get("Status")
    assert health_status in [
        "healthy",
        "starting",
    ], f"Unexpected health status: {health_status}"


@patch("resources.setup_resource.SetupResource.wait_until_all_containers_healthy")
def test_cleanup_on_initialization_failure(
    mock_wait_until_all_containers_healthy, temp_dir
):
    """Test that cleanup happens if a runtime error occurs during initialization."""
    resource_id = "test_resource"
    mock_wait_until_all_containers_healthy.return_value = False

    with pytest.raises(RuntimeError) as exc_info:
        SetupResource(
            resource_id,
            SetupResourceConfig(
                bounty_level_setup=False,
                task_dir=Path("bountybench/lunary"),
                bounty_number="0",
            ),
        )

    assert "Failed to wait until all containers healthy" in str(exc_info.value)
    result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
    assert (
        "lunary-app" not in result.stdout and "lunary-postgres" not in result.stdout
    ), "Containers were not cleaned up properly."


def test_error_handling(temp_dir):
    """Test error scenarios for SetupResource."""
    # Test with non-existent directory
    with pytest.raises(ValueError, match="Invalid task_dir"):
        SetupResource(
            "test_error",
            SetupResourceConfig(False, Path("/path/to/nonexistent/directory")),
        )

    # Test with invalid setup script
    invalid_script_path = temp_dir / "setup_repo_env.sh"
    invalid_script_path.write_text("exit 1")  # Always failing script
    invalid_script_path.chmod(0o755)

    with pytest.raises(RuntimeError, match="Setup script failed with return code 1"):
        SetupResource("test_invalid_script", SetupResourceConfig(False, temp_dir))
