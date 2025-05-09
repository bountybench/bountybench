import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import docker
import pytest

from resources.base_setup_resource import BaseSetupResource
from resources.bounty_setup_resource import (
    SETUP_FILES_DIR,
    BountySetupResource,
    BountySetupResourceConfig,
)
from resources.repo_setup_resource import RepoSetupResource, RepoSetupResourceConfig


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

    resource = RepoSetupResource("test", RepoSetupResourceConfig(temp_dir))
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

    resource = RepoSetupResource("test2", RepoSetupResourceConfig(temp_dir))
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
    resource = RepoSetupResource("test_restart", RepoSetupResourceConfig(temp_dir))

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

    resource = RepoSetupResource("test_health", RepoSetupResourceConfig(temp_dir))

    client = docker.from_env()
    container = client.containers.get("test_redis_server")
    time.sleep(10)
    container.reload()

    health_status = container.attrs["State"].get("Health", {}).get("Status")
    assert health_status in [
        "healthy",
        "starting",
    ], f"Unexpected health status: {health_status}"


def test_cleanup_on_initialization_failure(temp_dir):
    """Test that cleanup happens if a runtime error occurs during initialization."""
    resource_id = "test_resource"
    test_container_name = "test_container_cleanup_test"

    # Make sure the container is not running at the start of the test
    subprocess.run(["docker", "stop", test_container_name], capture_output=True)
    subprocess.run(["docker", "rm", test_container_name], capture_output=True)

    try:
        # Create a test directory structure for the bounty setup
        bounty_dir = Path(temp_dir) / "bounties" / "bounty_0" / "setup_files"
        bounty_dir.mkdir(parents=True, exist_ok=True)

        # Add a test setup script that doesn't actually create a container
        # We'll mock the container creation
        setup_script = bounty_dir / "setup_bounty_env.sh"
        setup_script.write_text(
            f"""
            echo "Container {test_container_name} Started"
            exit 0
        """
        )
        setup_script.chmod(0o755)

        with patch.object(BaseSetupResource, "stop") as mock_stop:
            with patch.object(
                BaseSetupResource,
                "extract_container_names",
                return_value=[test_container_name],
            ):
                with patch.object(
                    BaseSetupResource, "wait_until_all_containers_healthy"
                ) as mock_health_check:
                    mock_health_check.side_effect = RuntimeError(
                        "Failed to wait until all containers healthy"
                    )

                    # The test should raise the expected RuntimeError
                    with pytest.raises(RuntimeError) as exc_info:
                        BountySetupResource(
                            resource_id,
                            BountySetupResourceConfig(
                                task_dir=temp_dir,
                                bounty_number="0",
                            ),
                        )

                    assert "Failed to wait until all containers healthy" in str(
                        exc_info.value
                    )

                    # Verify that stop was called to clean up containers
                    assert (
                        mock_stop.called
                    ), "The stop method was not called to clean up containers"

    finally:
        # Ensure cleanup even if the test fails
        subprocess.run(["docker", "stop", test_container_name], capture_output=True)
        subprocess.run(["docker", "rm", test_container_name], capture_output=True)


def test_error_handling(temp_dir):
    """Test error scenarios for SetupResource."""
    # Test with non-existent directory
    with pytest.raises(ValueError, match="Invalid task_dir"):
        RepoSetupResource(
            "test_error",
            RepoSetupResourceConfig(Path("/path/to/nonexistent/directory")),
        )

    # Test with invalid setup script
    invalid_script_path = temp_dir / "setup_repo_env.sh"
    invalid_script_path.write_text("exit 1")  # Always failing script
    invalid_script_path.chmod(0o755)

    with pytest.raises(RuntimeError, match="Unable to successfully execute"):
        RepoSetupResource("test_invalid_script", RepoSetupResourceConfig(temp_dir))


@pytest.fixture
def mock_bounty_setup_resource():
    """Create a mock BountySetupResource for testing update_work_dir"""
    with patch("resources.base_setup_resource.run_command") as mock_run_command:
        mock_run_command.return_value = Mock(returncode=0, stdout=b"", stderr=b"")

        # Create a temporary task directory structure for testing
        test_task_dir = Path("/tmp/test_task_dir")

        # Mock the Path.exists and Path.is_dir to return True
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "is_dir", return_value=True),
        ):

            # Create a mock config
            config = BountySetupResourceConfig(
                task_dir=test_task_dir, bounty_number="123"
            )

            # Create the resource with setup mocked
            with patch.object(BountySetupResource, "setup", return_value=None):
                resource = BountySetupResource("test_resource", config)

                # Mock the initial work_dir
                resource.work_dir = (
                    test_task_dir / "bounties" / "bounty_123" / SETUP_FILES_DIR
                )

                yield resource


def test_update_work_dir_success(mock_bounty_setup_resource):
    """Test successful update of work_dir"""
    new_work_dir = Path("/tmp/new_location") / SETUP_FILES_DIR
    old_work_dir = mock_bounty_setup_resource.work_dir

    # Mock stop method to avoid actual stopping of resources
    with (
        patch.object(mock_bounty_setup_resource, "stop"),
        patch("resources.bounty_setup_resource.logger") as mock_logger,
    ):

        mock_bounty_setup_resource.update_work_dir(new_work_dir)

        # Verify work_dir was updated
        assert mock_bounty_setup_resource.work_dir == new_work_dir

        # Verify logs were called
        mock_logger.debug.assert_any_call(
            f"Stopping current bounty resource in {old_work_dir}"
        )
        mock_logger.debug.assert_any_call(
            f"Updated work_dir from {old_work_dir} to {new_work_dir}"
        )


def test_update_work_dir_not_exists(mock_bounty_setup_resource):
    """Test with a directory that doesn't exist"""
    new_work_dir = Path("/tmp/nonexistent_dir") / SETUP_FILES_DIR

    # Mock Path.exists to return False for the new work_dir
    with (
        patch.object(Path, "exists", lambda self: str(self) != str(new_work_dir)),
        patch.object(mock_bounty_setup_resource, "stop"),
    ):

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            mock_bounty_setup_resource.update_work_dir(new_work_dir)


def test_update_work_dir_wrong_dirname(mock_bounty_setup_resource):
    """Test with a directory that has wrong name (not setup_files)"""
    new_work_dir = Path("/tmp/wrong_dir_name")

    with patch.object(mock_bounty_setup_resource, "stop"):
        # Should raise ValueError
        with pytest.raises(ValueError):
            mock_bounty_setup_resource.update_work_dir(new_work_dir)


def test_update_work_dir_stops_old_resources(mock_bounty_setup_resource):
    """Test that stop is called on the old work_dir"""
    new_work_dir = Path("/tmp/new_location") / SETUP_FILES_DIR

    # Mock the stop method
    with patch.object(mock_bounty_setup_resource, "stop") as mock_stop:
        mock_bounty_setup_resource.update_work_dir(new_work_dir)

        # Verify stop was called
        mock_stop.assert_called_once()


def test_skip_setup_start(temp_dir):
    """Test that _start skips setup when skip_setup is True"""
    # Create a mock setup script that would fail if executed
    test_file_path = temp_dir / "setup_repo_env.sh"
    test_file_path.write_text("exit 1")  # This would fail if actually run
    test_file_path.chmod(0o755)

    # Create a resource with normal config but setup mocked to avoid actual execution
    with patch.object(BaseSetupResource, "_start"):
        resource = RepoSetupResource("test_skip", RepoSetupResourceConfig(temp_dir))

    # Now set skip_setup to True
    resource.skip_setup = True

    # Test _start method directly
    with patch("resources.base_setup_resource.logger") as mock_logger:
        resource._start()

        # Verify that the appropriate message was logged
        mock_logger.debug.assert_called_once_with(
            f"Skipping setup for {resource.setup_script_name}"
        )


def test_skip_setup_restart(temp_dir):
    """Test that restart skips setup when skip_setup is True"""
    # Create a mock setup script that would fail if executed
    test_file_path = temp_dir / "setup_repo_env.sh"
    test_file_path.write_text("exit 1")  # This would fail if actually run
    test_file_path.chmod(0o755)

    # Create a resource with normal config but setup mocked
    with patch.object(BaseSetupResource, "_start"):
        resource = RepoSetupResource(
            "test_skip_restart", RepoSetupResourceConfig(temp_dir)
        )

    # Set skip_setup to True
    resource.skip_setup = True

    with (
        patch.object(resource, "stop") as mock_stop,
        patch("resources.base_setup_resource.logger") as mock_logger,
    ):

        # Call restart - it should call stop and then _start which should skip
        resource.restart()

        # Verify that stop was called
        mock_stop.assert_called_once()

        # Verify the skip message was logged by _start during restart
        mock_logger.debug.assert_called_once_with(
            f"Skipping setup for {resource.setup_script_name}"
        )
