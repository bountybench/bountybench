import atexit
import logging
import os
import re
import subprocess
import sys
import time
from queue import Queue

import yaml

from resources.base_resource import BaseResource
from resources.resource_dict import resource_dict
from resources.utils import run_command
from utils.logger import get_main_logger

# Configure logging
logger = get_main_logger(__name__)


class TaskServerResource(BaseResource):
    """Task Server Resource"""

    def __init__(self, task_repo_dir: str, files_dir: str, server_address: str, require_setup: bool = False) -> None:
        try:
            # Split the server_address into hostname and port
            host_name, port_number = server_address.split(":")
        except ValueError:
            # Log error if the server_address format is invalid
            logger.error(
                f"Invalid server_address format: {server_address}. Expected format: hostname:port"
            )
            sys.exit(1)
        self.resource_id = server_address
        self.task_repo_dir = os.path.abspath(task_repo_dir)
        self.files_dir = files_dir
        self.require_setup = require_setup

        self.host_name = host_name
        self.port_number = port_number

        self.container_names = None
        self.health_check_timeout = 120
        self.start()

        resource_dict[self.resource_id] = self
        atexit.register(self.stop)

    def start(self) -> None:
        if self.require_setup:
            original_files_dir = os.path.join(
                self.task_repo_dir, self.files_dir)
            setup_file_dir = os.path.join(
                self.task_repo_dir, "setup_files", "flag.patch")
            logger.info(f"Apply setup to {original_files_dir}")
            subprocess.check_call(
                ['git', 'apply', setup_file_dir], cwd=original_files_dir)
        try:
            logger.info("Executing start_docker.sh")
            result = run_command(
                command=["./start_docker.sh"],
                work_dir=str(self.task_repo_dir),
            )
            logger.info(f"Spun up task server at {self.resource_id}")
            # Extract the container name(s) from stdout or stderr
            self.container_names = self.extract_container_names(
                result.stdout, result.stderr)
            if not self.container_names:
                raise ValueError(
                    f"Failed to retrieve container name(s) for {self.host_name}")
        except Exception as e:
            # Handle errors
            logger.error(
                f"Unable to spin up task server at {self.resource_id}.")
            sys.exit(1)

        self.wait_until_all_containers_healthy()
        if self.require_setup:
            original_files_dir = os.path.join(
                self.task_repo_dir, self.files_dir)
            setup_file_dir = os.path.join(
                self.task_repo_dir, "setup_files", "flag.patch")
            logger.info(f"Revert setup to {original_files_dir}")
            subprocess.check_call(
                ['git', 'apply', '--reverse', setup_file_dir], cwd=original_files_dir)

    def restart(self) -> None:
        self.stop()
        logger.info(f"Restarting task server {self.resource_id}")
        logger.info("Executing start_docker.sh")
        result = run_command(
            command=["./start_docker.sh"],
            work_dir=str(self.task_repo_dir),
        )
        logger.info(f"Spun up task server at {self.resource_id}")
        # Extract the container name(s) from stdout or stderr
        self.container_names = self.extract_container_names(
            result.stdout, result.stderr)
        if not self.container_names:
            raise Exception(
                f"Failed to retrieve container name(s) for {self.host_name}")

        self.wait_until_all_containers_healthy()

    def stop(self) -> None:
        try:
            logger.info("Executing stop_docker.sh")
            result = run_command(
                command=["./stop_docker.sh"],
                work_dir=str(self.task_repo_dir),
            )
            # Print the output
            logger.info(f"Stop task server at {self.resource_id}.")
        except FileNotFoundError:
            # Handle errors
            logger.warning(
                f"Stop script not found: {self.task_repo_dir}/stop_docker.sh.")
        except Exception as e:
            logger.info(f"Unable to stop task server at {self.resource_id}.")

    def wait_until_all_containers_healthy(self, timeout=300, check_interval=2):
        """
        Wait until all Docker containers' health status is 'healthy'.
        Processes containers in a queue and checks each one until it becomes healthy.
        Raises an exception if the timeout is reached before all containers are healthy.
        """
        # Initialize the container queue with all container names
        container_queue = Queue()
        for container in self.container_names:
            container_queue.put(container)

        if container_queue.empty():
            logger.error("No container names available for health check.")
            raise ValueError("No container names available for health check.")

        start_time = time.time()

        while not container_queue.empty():
            # Peek at the front of the queue
            container = container_queue.queue[0]
            # Check health status of the current container
            logger.info(f"Checking health of container {container}")
            inspect_result = run_command(
                command=[
                    "docker", "inspect", "--format={{json .State.Health.Status}}", container]
            )
            health_status = inspect_result.stdout.strip().strip("'\"")

            if health_status == "healthy":
                logger.info(f"Container '{container}' is healthy.")
                container_queue.get()  # Remove the container from the queue
            elif health_status in ["starting"]:
                logger.info(
                    f"Container '{container}' health status: {health_status}. Waiting...")
            else:
                raise Exception(
                    f"Container '{container}' has unexpected health status: {health_status}.")

            # Timeout check
            if time.time() - start_time > timeout:
                raise TimeoutError(
                    f"Timeout: Not all containers became healthy within {timeout} seconds.")

            time.sleep(check_interval)

        logger.info("All containers are healthy.")
        return True

    def extract_container_names(self, stdout=None, stderr=None):
        """
        Extract the names of all running containers.
        """
        # This pattern matches "Container <name> <status>"
        container_name_pattern = re.compile(
            r"Container\s+([^\s]+)\s+(Started|Healthy)")

        # Ensure both stdout and stderr are strings
        if stdout is None:
            stdout = ""
        if stderr is None:
            stderr = ""

        if not isinstance(stdout, str):
            stdout = stdout.decode(
                "utf-8") if isinstance(stdout, bytes) else ""
        if not isinstance(stderr, str):
            stderr = stderr.decode(
                "utf-8") if isinstance(stderr, bytes) else ""

        # Search in both stdout and stderr for container names
        output = stdout + stderr

        # Find all matches of container names with the specified statuses (Started/Healthy)
        matches = container_name_pattern.findall(output)

        if matches:
            # Extract unique container names
            # Use a set to ensure uniqueness
            container_names = list({match[0] for match in matches})
            logger.info(f"Container names extracted: {container_names}")
            return container_names
        else:
            logger.warning("No container names found in the output.")
            return []
