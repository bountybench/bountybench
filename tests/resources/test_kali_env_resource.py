import shutil
import tempfile
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, call, patch

import docker
import pytest

from resources.kali_env_resource import KaliEnvResource, KaliEnvResourceConfig
from resources.kali_env_resource_util import DockerContainerStartError

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
        resource_id=CONTAINER_NAME,
        config=KaliEnvResourceConfig(
            volumes=volume, task_dir=test_files_dir, bounty_number="0"
        ),
    )

    yield resource
    resource.stop()
    shutil.rmtree(temp_dir)
    print(f"Removed temporary test directory: {temp_dir}")


def test_docker_api_error_on_start():
    """Test if Docker API error is handled when starting the container."""

    with patch("docker.from_env") as MockDocker:
        mock_client = MagicMock()
        mock_containers = MagicMock()
        mock_client.containers = mock_containers
        mock_containers.run.side_effect = docker.errors.APIError("API error")
        MockDocker.return_value = mock_client

        # Patch the _remove_existing_container method to do nothing
        with patch.object(KaliEnvResource, "_remove_existing_container") as mock_remove:
            mock_remove.return_value = None
            mock_remove.side_effect = None

            with pytest.raises(DockerContainerStartError, match=".*Docker API error.*"):
                KaliEnvResource(
                    resource_id=CONTAINER_NAME,
                    config=KaliEnvResourceConfig(volumes=VOLUME),
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
        with patch.object(KaliEnvResource, "_remove_existing_container") as mock_remove:
            mock_remove.return_value = None
            mock_remove.side_effect = None

            with pytest.raises(
                DockerContainerStartError,
                match="Container failed to reach running state.",
            ):
                KaliEnvResource(
                    resource_id=CONTAINER_NAME,
                    config=KaliEnvResourceConfig(volumes=VOLUME),
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


@patch.object(KaliEnvResource, "run_command")
def test_is_python_repo(mock_run_command, kali_env_resource):
    """Test the detection of Python repositories."""
    # Test case 1: Repository with setup.py
    mock_run_command.return_value = ("/app/codebase/setup.py", "")
    assert kali_env_resource._is_python_repo("/app/codebase") is True

    # Test case 2: Repository with pyproject.toml
    mock_run_command.return_value = ("/app/codebase/pyproject.toml", "")
    assert kali_env_resource._is_python_repo("/app/codebase") is True

    # Test case 3: Not a Python repository
    mock_run_command.return_value = ("", "")
    assert kali_env_resource._is_python_repo("/app/codebase") is False


@patch.object(KaliEnvResource, "run_command")
def test_is_node_repo(mock_run_command, kali_env_resource):
    """Test the detection of Node.js repositories."""
    # Test case 1: Repository with package.json
    mock_run_command.return_value = ("/app/codebase/package.json", "")
    assert kali_env_resource._is_node_repo("/app/codebase") is True

    # Test case 2: Not a Node.js repository
    mock_run_command.return_value = ("", "")
    assert kali_env_resource._is_node_repo("/app/codebase") is False


@patch.object(KaliEnvResource, "_is_python_repo")
@patch.object(KaliEnvResource, "_is_node_repo")
@patch.object(KaliEnvResource, "run_command")
def test_install_python_repo(
    mock_run_command, mock_is_node, mock_is_python, kali_env_resource
):
    """Test the installation of Python repositories."""
    # Setup mocks
    mock_is_python.return_value = True
    mock_is_node.return_value = False
    mock_run_command.return_value = ("Successfully installed package", "")

    # Run the method directly, not through _initialize_bounty_directory
    kali_env_resource._install_repo_in_editable_mode()

    # Verify the pip install command was called
    mock_run_command.assert_has_calls(
        [
            mock.call(
                "[ -d /app/codebase ] && echo 'exists' || echo 'not_exists'", 120
            ),
            mock.call("pip install -e /app/codebase", 120),
        ],
        any_order=False,
    )


@patch.object(KaliEnvResource, "_is_python_repo")
@patch.object(KaliEnvResource, "_is_node_repo")
@patch.object(KaliEnvResource, "run_command")
def test_install_node_repo(
    mock_run_command, mock_is_node, mock_is_python, kali_env_resource
):
    """Test the installation of Node.js repositories - should now skip installation."""
    # Setup mocks
    mock_is_python.return_value = False
    mock_is_node.return_value = True
    mock_run_command.return_value = ("exists", "")

    # Run the method directly
    kali_env_resource._install_repo_in_editable_mode()

    # Verify run command only called once (to verify codebase exist) - we should skip Node.js installation

    mock_run_command.assert_called_once_with(
        "[ -d /app/codebase ] && echo 'exists' || echo 'not_exists'", 120
    )


@patch.object(KaliEnvResource, "_is_python_repo")
@patch.object(KaliEnvResource, "_is_node_repo")
@patch.object(KaliEnvResource, "run_command")
def test_no_repo_found(
    mock_run_command, mock_is_node, mock_is_python, kali_env_resource
):
    """Test the case when no recognized repository is found."""
    # Setup mocks
    mock_is_python.return_value = False
    mock_is_node.return_value = False
    mock_run_command.return_value = ("exists", "")

    # Run the method directly
    kali_env_resource._install_repo_in_editable_mode()

    # Verify both repo checks were called
    mock_is_python.assert_called_once_with("/app/codebase")
    mock_is_node.assert_called_once_with("/app/codebase")
