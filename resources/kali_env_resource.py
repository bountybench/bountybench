import atexit
import os
import sys
import threading
import time
from queue import Queue
from typing import Dict, Optional, Tuple

import docker
from docker.models.containers import Container

from resources.base_resource import BaseResource
from resources.resource_dict import resource_dict
from resources.utils import get_stdout_text, parse_shell_script
from utils.logger import get_main_logger

# Configure logging
logger = get_main_logger(__name__)

# Constants with type annotations
DOCKER_IMAGE: str = "cybench/cybounty:latest"
ENTRYPOINT: str = "/usr/local/bin/dockerd-entrypoint.sh"

MAX_RETRIES = 3
RETRY_DELAY = 10


class KaliEnvResource(BaseResource):
    """Kali Linux Environment Resource"""

    def __init__(self, name: str, task_repo_dir: str = None, bounty_number: str=None, volumes: Optional[Dict[str, Dict[str, str]]] = None) -> None:
        """
        Initialize the Kali Linux Environment with optional volume bindings.

        Args:
            name (str): The name of the container.
            task_repo_dir (str, optional): The directory path of the task repository containing scripts or requirements.
            volumes (Optional[Dict[str, Dict[str, str]]]): Docker volume bindings in the format {host_path: {'bind': container_path, 'mode': rw}}.
        """
        self.client: docker.DockerClient = docker.from_env()
        self.resource_id = name
        self.container: Container = self.start(self.resource_id, volumes)
        self.bounty_dir = os.path.join(
                str(task_repo_dir) + "/bounties/bounty_" + bounty_number
        )
        if task_repo_dir:
            self.run_requirements(self.bounty_dir )

        resource_dict[self.resource_id] = self
        atexit.register(self.stop)

    def start(
        self, name: str, volumes: Optional[Dict[str, Dict[str, str]]]
    ) -> Container:
        """
        Start a Kali Linux container to be used throughout the lifecycle.

        Args:
            name (str): The name of the container.
            volumes (Optional[Dict[str, Dict[str, str]]]): Docker volume bindings in the format {host_path: {'bind': container_path, 'mode': rw}}.

        Returns:
            Container: The started Docker container.

        Raises:
            SystemExit: If the container fails to start after MAX_RETRIES attempts.
        """
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(
                    f"Starting a new Docker container (Attempt {attempt + 1}/{MAX_RETRIES})...")
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
                logger.error(
                    f"Failed to start Docker container (Attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(
                        f"All {MAX_RETRIES} attempts to start the container have failed.")
                    sys.exit(1)

    def stop(self) -> None:
        """
        Stop and remove the Docker container when the program exits.

        This function is automatically registered to run when the program terminates.
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
            command (str): The command to execute inside the container.
            timeout (int): Maximum time to wait for the command to execute, in seconds. Defaults to 60.
            workdir (Optional[str]): The working directory inside the container to execute the command. Defaults to None.

        Returns:
            Tuple[str, str]: A tuple containing stdout and stderr output as strings.
        """
        logger.info(f"Running command in Docker container: {command}")

        result_queue: Queue = Queue()
        stop_event = threading.Event()

        def exec_command() -> None:
            """
            Execute the command inside the Docker container and put the result in the queue.

            Uses Docker's exec_run method to run the command inside the container.
            """
            try:
                exec_result: docker.models.exec.ExecResult = self.container.exec_run(
                    cmd=["/bin/bash", "-c", command],
                    stdout=True,
                    stderr=True,
                    workdir=workdir,
                    demux=True,
                )
                if not stop_event.is_set():
                    stdout: bytes = exec_result.output[0]
                    stderr: bytes = exec_result.output[1]
                    result_queue.put((stdout, stderr))
            except Exception as e:
                if not stop_event.is_set():
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
                f"Command '{command}' timed out after {timeout} seconds. Stopping the command thread.")
            stop_event.set()
            command_thread.join()  # Ensure the thread stops
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
        Execute any required setup scripts from the provided repository directory.

        Args:
            task_repo_dir (str): Path to the repository directory containing the metadata/requirements.sh script.
        """
        requirements_path = f"{task_repo_dir}/setup_files/requirements.sh"
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

    def parse_target_host(self, target_host: str) -> Tuple[str, int]:
        """
        Parse the target host string into hostname and port.

        Args:
            target_host (str): The target host in the format hostname:port.

        Returns:
            Tuple[str, int]: A tuple containing the hostname and port as an integer.
        """
        try:
            hostname, port = target_host.split(":")
            return hostname, int(port)
        except ValueError:
            logger.error(
                f"Invalid target_host format: {target_host}. Expected format: hostname:port")
            sys.exit(1)

    def health_check(self, target_hosts: str) -> None:
        """
        Perform health checks on the specified target hosts with retries.

        Args:
            target_hosts (str): A string containing space-separated target hosts in the format hostname:port.
        """
        hosts = target_hosts.split()
        failed_hosts = []

        for target_host in hosts:
            hostname, port = self.parse_target_host(target_host)

            def nc_check():
                """
                Use netcat to check if the specified hostname and port are open.

                Returns:
                    bool: True if the port is open, False otherwise.
                """
                stdout, stderr = self.run_command(
                    f"nc -zv -w 5 {hostname} {port}", timeout=10)
                logger.info(f"Netcat check output: {stdout}\n {stderr}")
                return "open" in stderr

            def http_check():
                """
                Use curl to check if the specified hostname and port respond with an HTTP 200 status.

                Returns:
                    bool: True if the HTTP response code is 200, False otherwise.
                """
                stdout, stderr = self.run_command(
                    f"curl -sS -o /dev/null -w \"%{{http_code}}\" {hostname}:{port}", timeout=10)
                status_code = int(stdout)
                logger.info(f"HTTP check output: {stdout}\n {stderr}")
                return status_code == 200

            for attempt in range(MAX_RETRIES):
                if http_check() or nc_check():
                    logger.info(
                        f"Health check passed for {hostname}:{port} on attempt {attempt + 1}.")
                    break
                else:
                    logger.warning(
                        f"Health check failed for {hostname}:{port} (Attempt {attempt + 1}/{MAX_RETRIES}).")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                    else:
                        failed_hosts.append(target_host)

        if failed_hosts:
            logger.error(
                f"Health checks failed for the following hosts: {', '.join(failed_hosts)}")
            raise RuntimeError(
                "Health checks failed for one or more target hosts.")
        else:
            logger.info("All target hosts passed the health check.")