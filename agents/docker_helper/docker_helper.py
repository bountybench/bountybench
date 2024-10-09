import atexit
import logging
import threading
from pathlib import Path
from queue import Queue
from typing import Tuple

import docker
from docker.models.containers import Container

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DOCKER_IMAGE = "cybench/cybounty:latest"
ENTRYPOINT = "/usr/local/bin/dockerd-entrypoint.sh"


def get_stdout_text(process_output) -> str:
    stdout = ""
    try:
        stdout = process_output.decode("utf-8")
    except UnicodeDecodeError as e:
        stdout = f"This failed to decode. Remember: the problem is fully solveable using UTF-8 encoding. Ignore any images (jpeg, png, etc.), videos (mp4, mpeg) etc.  Error: {str(e)}"
    return stdout


class DockerHelper:
    """Class to handle Docker operations."""

    def __init__(self, volumes=None):
        self.client = docker.from_env()
        self.container = self._start_container(volumes)
        atexit.register(self._stop_container)

    def _start_container(self, volumes) -> Container:
        """Start a Docker container to be used throughout the lifecycle."""
        try:
            logger.info("Starting a new Docker container...")
            container = self.client.containers.run(
                DOCKER_IMAGE,
                cgroupns="host",
                volumes=volumes,
                network="shared_net",
                entrypoint=ENTRYPOINT,
                detach=True,
                name="cybench",
            )
            logger.info("Docker container started successfully.")
            return container
        except Exception as e:
            logger.error(f"Failed to start Docker container: {e}")
            raise
    
    def _stop_container(self):
        """Stop and remove the container when the program ends."""
        if self.container:
            logger.info("Cleaning up: stopping and removing Docker container.")
            try:
                self.container.stop()
                self.container.remove()
                logger.info("Docker container cleaned up successfully.")
            except Exception as e:
                logger.error(f"Error cleaning up Docker container: {e}")


    def run_command(self, command: str, workdir: str,
                    timeout: int = 60) -> Tuple[str, str]:
        """Run a command inside the running container with a timeout."""
        logger.info(f"Running command in Docker container: {command}")

        result_queue = Queue()

        def exec_command():
            try:
                exec_result = self.container.exec_run(
                    cmd=["/bin/bash", "-c", command],
                    stdout=True,
                    stderr=True,
                    workdir=workdir,
                    demux=True,
                )
                stdout, stderr = exec_result.output
                result_queue.put((stdout, stderr))
            except Exception as e:
                logger.error(
                    f"Failed to execute command in Docker container: {e}")
                result_queue.put((None, f"Exception occurred: {e}"))

        # Start the command thread
        command_thread = threading.Thread(target=exec_command)
        command_thread.start()
        command_thread.join(timeout)

        if command_thread.is_alive():
            # If command hasn't finished, kill it
            logger.warning(
                f"Command '{command}' timed out after {timeout} seconds.")
            stderr = get_stdout_text(stderr) if stderr else ""
            return f"Command '{command}' timed out after {timeout} seconds.", ""

        # If the command finished, retrieve results from the queue
        if not result_queue.empty():
            stdout, stderr = result_queue.get()
            stdout = get_stdout_text(stdout) if stdout else ""
            stderr = get_stdout_text(stderr) if stderr else ""
            logger.info(
                f"Command executed successfully.\nstdout: {stdout}\nstderr: {stderr}")
            return stdout, stderr

        return "", "Failed to retrieve output from the command."