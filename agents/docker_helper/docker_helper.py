import atexit
import logging
import threading
from queue import Queue
from typing import Dict, Optional, Tuple

import docker
from docker.models.containers import Container

# Configure logging
logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)

# Constants with type annotations
DOCKER_IMAGE: str = "cybench/cybounty:latest"
ENTRYPOINT: str = "/usr/local/bin/dockerd-entrypoint.sh"


def get_stdout_text(process_output: bytes) -> str:
    """
    Decode the process output from bytes to a UTF-8 string.

    Args:
        process_output (bytes): The output to decode.

    Returns:
        str: The decoded string or an error message if decoding fails.
    """
    stdout: str = ""
    if process_output is None:
        return stdout
    try:
        stdout = process_output.decode("utf-8")
        return stdout
    except UnicodeDecodeError as e:
        stdout = (
            "This failed to decode. Remember: the problem is fully solvable using UTF-8 encoding. "
            "Ignore any images (jpeg, png, etc.), videos (mp4, mpeg) etc. "
            f"Error: {str(e)}"
        )


class DockerHelper:
    """Class to handle Docker operations."""

    def __init__(self, name: str, volumes: Optional[Dict[str, Dict[str, str]]] = None) -> None:
        """
        Initialize the DockerHelper with optional volume bindings.

        Args:
            name (str): The name of the container.
            volumes (Optional[Dict[str, Dict[str, str]]]): Docker volume bindings.
        """
        self.client: docker.DockerClient = docker.from_env()
        self.container: Container = self._start_container(name, volumes)
        atexit.register(self._stop_container)

    def _start_container(
        self, name: str, volumes: Optional[Dict[str, Dict[str, str]]]
    ) -> Container:
        """
        Start a Docker container to be used throughout the lifecycle.

        Args:
            name (str): The name of the container.
            volumes (Optional[Dict[str, Dict[str, str]]]): Docker volume bindings.

        Returns:
            Container: The started Docker container.

        Raises:
            Exception: If the container fails to start.
        """
        try:
            logger.info("Starting a new Docker container...")
            container: Container = self.client.containers.run(
                image=DOCKER_IMAGE,
                cgroupns="host",
                volumes=volumes,
                network="shared_net",
                entrypoint=ENTRYPOINT,
                detach=True,
                name=name,
            )
            logger.info("Docker container started successfully.")
            return container
        except Exception as e:
            logger.error(f"Failed to start Docker container: {e}")
            raise

    def _stop_container(self) -> None:
        """
        Stop and remove the Docker container when the program exits.
        """
        if self.container:
            logger.info("Cleaning up: stopping and removing Docker container.")
            try:
                self.container.stop()
                self.container.remove()
                logger.info("Docker container cleaned up successfully.")
            except Exception as e:
                logger.error(f"Error cleaning up Docker container: {e}")

    def run_command(
        self, command: str, timeout: int = 60, workdir: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Run a command inside the running container with a timeout.

        Args:
            command (str): The command to execute.
            timeout (int): Timeout in seconds. Defaults to 60.
            workdir (Optional[str]): The working directory inside the container.

        Returns:
            Tuple[str, str]: A tuple containing stdout and stderr as strings.
        """
        logger.info(f"Running command in Docker container: {command}")

        result_queue: Queue = Queue()

        def exec_command() -> None:
            """
            Execute the command inside the Docker container and put the result in the queue.
            """
            try:
                exec_result: docker.models.exec.ExecResult = self.container.exec_run(
                    cmd=["/bin/bash", "-c", command],
                    stdout=True,
                    stderr=True,
                    workdir=workdir,
                    demux=True,
                )
                stdout: bytes = exec_result.output[0]
                stderr: bytes = exec_result.output[1]
                result_queue.put((stdout, stderr))
            except Exception as e:
                logger.error(
                    f"Failed to execute command in Docker container: {e}")
                result_queue.put(
                    (None, f"Exception occurred: {e}".encode("utf-8")))

        # Start the command thread
        command_thread: threading.Thread = threading.Thread(
            target=exec_command)
        command_thread.start()
        command_thread.join(timeout)

        if command_thread.is_alive():
            # If command hasn't finished, kill it
            logger.warning(
                f"Command '{command}' timed out after {timeout} seconds.")
            return f"Command '{command}' timed out after {timeout} seconds.", ""

        # If the command finished, retrieve results from the queue
        if not result_queue.empty():
            stdout_bytes: bytes
            stderr_bytes: bytes
            stdout_bytes, stderr_bytes = result_queue.get()
            stdout: str = get_stdout_text(stdout_bytes)
            stderr: str = get_stdout_text(stderr_bytes)
            logger.info(
                f"Command executed successfully.\nstdout: {stdout}\nstderr: {stderr}"
            )
            return stdout, stderr

        return "", "Failed to retrieve output from the command."
