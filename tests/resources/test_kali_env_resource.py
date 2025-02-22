import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import docker
import pytest

from resources.kali_env_resource import (
    DockerContainerStartError,
    KaliEnvResource,
    KaliEnvResourceConfig,
)

VOLUME = {
    Path(__file__).parent.resolve() / "test_files": {"bind": "/app/", "mode": "rw"}
}
CONTAINER_NAME = "test_container"


@pytest.fixture(scope="module")
def kali_env_resource():
    temp_dir = tempfile.mkdtemp()
    test_files_dir = Path(temp_dir)
    print(f"Created temporary test directory: {test_files_dir}")

    test_file_path = test_files_dir / "test.txt"
    with open(test_file_path, "w") as f:
        f.write("TEST{RANDOM_WORDS}")

    volume = {str(test_files_dir): {"bind": "/app", "mode": "rw"}}
    resource = KaliEnvResource(
        resource_id=CONTAINER_NAME, config=KaliEnvResourceConfig(volumes=volume)
    )

    yield resource
    resource.stop()
    shutil.rmtree(temp_dir)
    print(f"Removed temporary test directory: {temp_dir}")


def test_docker_api_error_on_start():
    """Test if Docker API error is handled when starting the container."""
    with patch("docker.from_env") as mock_docker:
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        mock_client.containers.run.side_effect = docker.errors.APIError("API error")

        with pytest.raises(
            DockerContainerStartError, match="Docker API error: API error"
        ):
            KaliEnvResource(
                resource_id=CONTAINER_NAME, config=KaliEnvResourceConfig(volumes=VOLUME)
            )


def test_container_start_timeout():
    """Test if timeout during container start is handled correctly."""
    with patch("docker.from_env") as mock_docker:
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_docker.return_value = mock_client

        mock_client.containers.run.return_value = mock_container
        mock_container.status = (
            "created"  # Simulate that container started but is not running
        )

        # Simulate the reload to always return 'created'
        mock_container.reload = MagicMock(side_effect=lambda: None)

        with pytest.raises(
            DockerContainerStartError, match="Container failed to reach running state."
        ):
            KaliEnvResource(
                resource_id=CONTAINER_NAME, config=KaliEnvResourceConfig(volumes=VOLUME)
            )


def test_container_removal_error():
    """Test if removal error is handled when a container already exists."""
    with patch("docker.from_env") as mock_docker:
        mock_client = MagicMock()
        mock_docker.return_value = mock_client
        existing_container = MagicMock()
        mock_client.containers.get.return_value = existing_container
        # The error should be raised here when tried to remove
        existing_container.remove.side_effect = docker.errors.APIError(
            "Failed to remove container"
        )

        with pytest.raises(
            DockerContainerStartError,
            match="Docker API error: Failed to remove container",
        ):
            KaliEnvResource(
                resource_id=CONTAINER_NAME, config=KaliEnvResourceConfig(volumes=VOLUME)
            )


def test_run_simple_command(kali_env_resource):
    command = "echo Hello"
    stdout, stderr = kali_env_resource.run_command(command)
    assert stdout.strip() == "Hello"
    assert stderr.strip() == ""


def test_run_multiple_commands(kali_env_resource):
    command = "echo Hello\n echo World"
    stdout, stderr = kali_env_resource.run_command(command)
    assert stdout.strip() == "Hello\nWorld"
    assert stderr.strip() == ""


def test_command_with_error(kali_env_resource):
    command = "ls /nonexistent_directory"
    stdout, stderr = kali_env_resource.run_command(command)
    assert stdout.strip() == ""
    assert "No such file or directory" in stderr


def test_command_with_volume(kali_env_resource):
    file_path = "/app/test.txt"
    command = f"ls -l /app && cat {file_path}"
    stdout, stderr = kali_env_resource.run_command(command)
    assert "TEST{RANDOM_WORDS}" in stdout.strip()
    assert stderr == ""


def test_command_with_timeout(kali_env_resource):
    command = "sleep 120"
    stdout, stderr = kali_env_resource.run_command(command, timeout=2)
    assert "timed out after 2 seconds" in stdout
    assert stderr.strip() == ""


def test_working_directory(kali_env_resource):
    command = "pwd"
    workdir = "/tmp"
    stdout, stderr = kali_env_resource.run_command(command, workdir=workdir)
    assert stdout.strip() == workdir
    assert stderr.strip() == ""


def test_write_and_read_file(kali_env_resource):
    file_path = "testfile.txt"
    write_command = f"echo 'Hello World' > {file_path}"
    read_command = f"cat {file_path}"

    kali_env_resource.run_command(write_command)
    stdout, stderr = kali_env_resource.run_command(read_command)
    assert stdout.strip() == "Hello World"
    assert stderr.strip() == ""
    kali_env_resource.run_command(f"rm {file_path}")


def test_invalid_command(kali_env_resource):
    command = "invalid_command_that_does_not_exist"
    stdout, stderr = kali_env_resource.run_command(command)
    assert stdout.strip() == ""
    assert "command not found" in stderr


def test_container_persistence(kali_env_resource):
    file_path = "persistent_testfile.txt"
    create_command = f"touch {file_path}"
    check_command = f"test -f {file_path} && echo Exists"

    kali_env_resource.run_command(create_command)
    stdout, stderr = kali_env_resource.run_command(check_command)
    assert stdout.strip() == "Exists"
    assert stderr.strip() == ""

    kali_env_resource.run_command(f"rm {file_path}")
    stdout, stderr = kali_env_resource.run_command(check_command)
    assert stdout.strip() == ""
    assert stderr.strip() == ""
