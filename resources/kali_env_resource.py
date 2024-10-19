import atexit
import logging
import os
import sys
import threading
from queue import Queue
from typing import Dict, List, Optional, Tuple

import docker
from docker.models.containers import Container

from resources.base_resource import BaseResource
from resources.resource_dict import resource_dict
from utils.logger import get_main_logger

# Configure logging
logger = get_main_logger(__name__)

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


def parse_shell_script(script_path: str) -> List[str]:
    """
    Parse a shell script into individual commands.
    Args:
        script_path (str): Path to the shell script.
    Returns:
        List[str]: A list of commands to execute.
    """
    if not os.path.isfile(script_path):
        raise FileNotFoundError(f"Shell script not found at {script_path}")

    commands = []
    with open(script_path, 'r') as script_file:
        for idx, line in enumerate(script_file, start=1):
            # Remove leading/trailing whitespace
            stripped_line = line.strip()

            # Skip empty lines and comments
            if not stripped_line or stripped_line.startswith("#"):
                continue

            # Add command to the list (assuming one command per line)
            commands.append(stripped_line)

    return commands


class KaliEnvResource(BaseResource):
    """Kali Linux Environment Resource"""

    def __init__(self, name: str, task_repo_dir: str = None, volumes: Optional[Dict[str, Dict[str, str]]] = None) -> None:
        """
        Initialize the Kali Linux Environment with optional volume bindings.

        Args:
            name (str): The name of the container.
            volumes (Optional[Dict[str, Dict[str, str]]]): Docker volume bindings.
        """
        self.client: docker.DockerClient = docker.from_env()
        self.resource_id = name
        self.container: Container = self.start(self.resource_id, volumes)
        if task_repo_dir:
            self.run_requirements(task_repo_dir)

        resource_dict[self.resource_id] = self
        atexit.register(self.stop)

    def start(
        self, name: str, volumes: Optional[Dict[str, Dict[str, str]]]
    ) -> Container:
        """
        Start a Kali Linux container to be used throughout the lifecycle.

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
            sys.exit(1)

    def stop(self) -> None:
        """
        Stop and remove the Docker container when the program exits.
        """
        if self.container:
            logger.info("Cleaning up: stopping and removing Docker container.")
            try:
                self.container.stop()
                self.container.remove()
                self.container = None
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

    def run_requirements(self, task_repo_dir: str) -> None:
        """
        Execute any required setup scripts.
        Args:
            task_repo_dir (str): Path to the repository directory for the task.
        """
        requirements_path = f"{task_repo_dir}/metadata/requirements.sh"
        if not os.path.isfile(requirements_path):
            logger.error(f"Requirements file not found at {requirements_path}")
            sys.exit(1)

        # Parse and execute the requirements script commands
        requirement_commands = parse_shell_script(requirements_path)
        for command in requirement_commands:
            stdout, stderr = self.run_command(command)

            # Log output and error for each command
            if stdout:
                logger.info(f"Requirements.sh Output:\n{stdout}")
            if stderr:
                logger.error(f"Requirements.sh Error:\n{stderr}")

    def health_check(self, target_hosts: str) -> None:
        """
        Perform health checks on the specified target hosts.
        Args:
            target_hosts (str): A string containing space-separated target hosts in the format hostname:port.
        """
        hosts = target_hosts.split()
        failed_hosts = []

        for target_host in hosts:
            try:
                # Split the target_host into hostname and port
                hostname, port = target_host.split(":")
                port = int(port)
            except ValueError:
                # Log error if the target_host format is invalid
                logger.error(
                    f"Invalid target_host format: {target_host}. Expected format: hostname:port"
                )
                sys.exit(1)

            def nc_check():
                # Run netcat to check if the specified port is open
                stdout, stderr = self.run_command(
                    command=f"nc -zv -w 5 {hostname} {port}", timeout=10)
                # Log the netcat command output
                logger.info(
                    f"Netcat check output: {stdout}\n {stderr}")
                if "open" in stderr:
                    return True
                else:
                    logger.error(f"Netcat check failed for {hostname}:{port}")
                    return False

            def http_check():
                # Run curl to check if the HTTP service is responding with status code 200
                stdout, stderr = self.run_command(
                    command=f"curl -sS -o /dev/null -w \"%{{http_code}}\" {hostname}:{port}", timeout=10)
                status_code = int(stdout)
                # Log the HTTP check command output
                logger.info(
                    f"HTTP check output: {stdout}\n {stderr}")
                if status_code == 200:
                    return True
                else:
                    logger.error(f"HTTP check failed for {hostname}:{port}")
                    return False

            # Perform health checks: first using HTTP check, then netcat check if necessary
            if not http_check() and not nc_check():
                logger.error(f"Health check failed for {hostname}:{port}")
                failed_hosts.append(target_host)

        # Log results of health checks
        if failed_hosts:
            logger.error(
                f"Health checks failed for the following hosts: {', '.join(failed_hosts)}"
            )
            sys.exit(1)
        else:
            logger.info("All target hosts passed the health check")
