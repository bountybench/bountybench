import concurrent.futures
import os
import shutil
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, call, patch

import docker
import pytest

from resources.kali_env_resource import (
    KaliEnvResource,
    KaliEnvResourceConfig,
    timeout_context,
)
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


def test_output_streaming(kali_env_resource):
    """Test that output is streamed in real-time rather than buffered."""

    test_output_stream_script = """#!/bin/bash
echo "Line 1"
sleep 0.5
echo "Line 2"
sleep 0.5
echo "Line 3" >&2
sleep 0.5
echo "Line 4"
sleep 0.5
echo "Line 5" >&2
"""
    # Capture timing of output arrival
    output_times = []
    original_stdout_write = sys.stdout.write
    original_stderr_write = sys.stderr.write

    def stdout_monitor(text):
        """Capture when output arrives at stdout."""
        output_times.append((time.time(), "stdout", text.strip()))
        return original_stdout_write(text)

    def stderr_monitor(text):
        """Capture when output arrives at stderr."""
        output_times.append((time.time(), "stderr", text.strip()))
        return original_stderr_write(text)

    # Patch stdout/stderr to monitor when output arrives
    sys.stdout.write = stdout_monitor
    sys.stderr.write = stderr_monitor

    start_time = time.time()

    try:
        kali_env_resource._run_non_tty_command(
            f"cat << 'EOF' > test_output_stream.sh\n{test_output_stream_script}\nEOF", timeout = 600
        )
        # Run the script, which should produce output with delay between lines
        stdout_text, stderr_text = kali_env_resource._run_non_tty_command(
            "chmod +x test_output_stream.sh && ./test_output_stream.sh", timeout = 600
        )

        # Restore stdout/stderr
        sys.stdout.write = original_stdout_write
        sys.stderr.write = original_stderr_write

        assert "Line 1" in stdout_text
        assert "Line 2" in stdout_text
        assert "Line 4" in stdout_text
        assert "Line 3" in stderr_text
        assert "Line 5" in stderr_text

        # Analyze timing to confirm streaming behavior
        # First, filter out empty lines
        actual_outputs = [item for item in output_times if item[2]]

        # Verify we have at least 5 output events
        assert (
            len(actual_outputs) >= 5
        ), f"Expected at least 5 output events, got {len(actual_outputs)}"

        # Calculate time differences between first and last outputs
        time_span = actual_outputs[-1][0] - actual_outputs[0][0]

        # If output is streamed, time_span should be close to 2 seconds (4 sleep periods)
        # If buffered, it would be close to 0
        assert (
            time_span >= 1.5
        ), f"Output appeared too quickly ({time_span}s), suggesting it was buffered, not streamed"

        # Print actual output timing for debugging
        print("\nOutput timing (seconds since start, stream, content):")
        for timestamp, stream, content in actual_outputs:
            print(f"{timestamp - start_time:.3f}s - {stream}: {content}")

    finally:
        # Make sure we restore stdout/stderr even if the test fails
        sys.stdout.write = original_stdout_write
        sys.stderr.write = original_stderr_write


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
                "[ -d /app/codebase ] && echo 'exists' || echo 'not_exists'", 600
            ),
            mock.call(
                command="pip install -e .", timeout=1200, workdir="/app/codebase"
            ),
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
        "[ -d /app/codebase ] && echo 'exists' || echo 'not_exists'", 600
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


def test_timeout_context_no_timeout():
    """Test that timeout_context works correctly when no timeout occurs."""
    with timeout_context(1):
        # Operation that takes less than the timeout
        time.sleep(0.1)
    # If we reach here, no exception was raised, which is the expected behavior


def test_timeout_context_with_timeout():
    """Test that timeout_context raises TimeoutError when timeout occurs."""
    with pytest.raises(TimeoutError):
        with timeout_context(0.1):
            # Operation that takes longer than the timeout
            time.sleep(0.5)


def test_timeout_context_nested():
    """Test that nested timeout_contexts work correctly."""
    # Outer timeout is longer than inner
    with timeout_context(1):
        # Should timeout from inner context
        with pytest.raises(TimeoutError):
            with timeout_context(0.1):
                time.sleep(0.5)
        # This should execute after inner timeout but before outer timeout
        time.sleep(0.2)

    # Inner timeout is longer than outer
    with pytest.raises(TimeoutError):
        with timeout_context(0.2):
            with timeout_context(1):
                time.sleep(0.5)  # Should timeout from outer context


def test_timeout_context_in_thread():
    """Test that timeout_context works when used in a non-main thread."""

    def thread_func():
        try:
            with timeout_context(0.1):
                time.sleep(0.5)
            return "No timeout occurred"
        except TimeoutError:
            return "Timeout occurred"

    # Run in a thread
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(thread_func)
        result = future.result()

    assert result == "Timeout occurred"


def test_timeout_context_cancellation():
    """Test that timeout_context properly cancels the timer when exiting normally."""
    # We'll use a flag to see if the timeout occurred after the context manager
    timeout_flag = [False]

    def set_timeout_flag():
        timeout_flag[0] = True

    # Create a mock version of timeout_context that sets our flag
    @contextmanager
    def test_timeout():
        timer = threading.Timer(0.2, set_timeout_flag)
        timer.daemon = True
        try:
            timer.start()
            yield
        finally:
            timer.cancel()

    with test_timeout():
        time.sleep(0.1)  # Less than the timeout

    # Sleep a bit longer than the timeout to ensure the timer would have fired
    time.sleep(0.3)

    # The timer should have been cancelled, so the flag should still be False
    assert timeout_flag[0] is False


def test_timeout_context_exception_handling():
    """Test that timeout_context correctly handles other exceptions."""

    class TestException(Exception):
        pass

    with pytest.raises(TestException):
        with timeout_context(1):
            raise TestException("Test exception")


def test_timeout_context_in_cpu_bound_operation():
    """Test timeout_context with a CPU-bound operation rather than I/O-bound."""

    def cpu_intensive_operation():
        result = 0
        for i in range(10000000):
            result += i
        return result

    with pytest.raises(TimeoutError):
        with timeout_context(0.1):
            cpu_intensive_operation()


def test_timeout_context_in_worker_thread_pool():
    """Test timeout_context when used in multiple worker threads simultaneously."""

    def worker_with_timeout(timeout_duration, sleep_duration):
        try:
            with timeout_context(timeout_duration):
                time.sleep(sleep_duration)
                return "Completed"
        except TimeoutError:
            return "Timed out"

    scenarios = [
        (0.5, 0.1),  # Should complete
        (0.5, 1.0),  # Should timeout
        (0.2, 0.1),  # Should complete
        (0.2, 0.5),  # Should timeout
    ]

    expected_results = ["Completed", "Timed out", "Completed", "Timed out"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(worker_with_timeout, t, s) for t, s in scenarios]
        results = [future.result() for future in futures]

    assert results == expected_results
