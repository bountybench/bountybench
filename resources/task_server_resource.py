import atexit
import logging
import os
from queue import Queue
import re
import sys
import time
import yaml

from resources.base_resource import BaseResource
from resources.resource_dict import resource_dict
from resources.utils import run_command

# Configure logging
logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)


class TaskServerResource(BaseResource):
    """Task Server Resource"""

    def __init__(self, task_repo_dir: str, server_address: str) -> None:
        try:
            # Split the server_address into hostname and port
            hostname, port = server_address.split(":")
        except ValueError:
            # Log error if the server_address format is invalid
            logger.error(
                f"Invalid server_address format: {server_address}. Expected format: hostname:port"
            )
            sys.exit(1)
        self.resource_id = server_address
        self.task_repo_dir = task_repo_dir
        self.host_name = hostname
        self.container_names = None
        self.health_check_timeout = 120
        self.start()

        resource_dict[self.resource_id] = self
        atexit.register(self.stop)

    def start(self) -> None:
        try:
            logger.info(f"Changing directory to {self.task_repo_dir}")
            os.chdir(self.task_repo_dir)

            logger.info("Executing start_docker.sh")
            result = run_command(
                command=["./start_docker.sh"],
                work_dir=str(self.task_repo_dir),
            )
            logger.info(f"Spun up task server at {self.resource_id}")
            # Extract the container name(s) from stdout or stderr
            self.container_names = self.extract_container_names(result.stdout, result.stderr)
            if not self.container_names:
                raise Exception(f"Failed to retrieve container name(s) for {self.host_name}")
        except Exception as e:
            # Handle errors
            logger.error(
                f"Unable to spin up task server at {self.resource_id}.")
            sys.exit(1)
        finally:
            # Return to the previous directory to ensure no side effects
            os.chdir('..')

        self.wait_until_all_containers_healthy()

    def stop(self) -> None:
        try:
            logger.info(f"Changing directory to {self.task_repo_dir}")
            os.chdir(self.task_repo_dir)

            logger.info("Executing stop_docker.sh")
            result = run_command(
                command=["./stop_docker.sh"],
                work_dir=str(self.task_repo_dir),
            )
            # Print the output
            logger.info(f"Stop task server at {self.resource_id}.")
        except FileNotFoundError:
            # Handle errors
            logger.warning(f"Stop script not found: {self.task_repo_dir}/stop_docker.sh.")
        except Exception as e:
            logger.info(f"Unable to stop task server at {self.resource_id}.")
        finally:
            # Return to the previous directory to ensure no side effects
            os.chdir('..')

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
            sys.exit(1)

        logger.info(f"Waiting for all containers to become healthy...")
        
        start_time = time.time()

        while not container_queue.empty():
            container = container_queue.queue[0]  # Peek at the front of the queue
            try:
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
                    logger.info(f"Container '{container}' health status: {health_status}. Waiting...")
                else:
                    logger.warning(f"Container '{container}' has unexpected health status: {health_status}.")
                    sys.exit(1)

            except Exception as e:
                logger.error(f"Unexpected error while checking health status of container '{container}': {e}")
                sys.exit(1)

            # Timeout check
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Timeout: Not all containers became healthy within {timeout} seconds.")

            time.sleep(check_interval)

        logger.info("All containers are healthy.")
        return True
    
    def extract_container_names(self, stdout=None, stderr=None):
        """
        Extract the names of all running containers.
        """
        # This pattern matches "Container <name> <status>"
        container_name_pattern = re.compile(r"Container\s+([^\s]+)\s+(Started|Healthy)")

        logger.info("Checking Docker container health status...")
        logger.info("{stderr}")
        # Ensure both stdout and stderr are strings
        if stdout is None:
            stdout = ""
        if stderr is None:
            stderr = ""

        if not isinstance(stdout, str):
            stdout = stdout.decode("utf-8") if isinstance(stdout, bytes) else ""
        if not isinstance(stderr, str):
            stderr = stderr.decode("utf-8") if isinstance(stderr, bytes) else ""

        # Search in both stdout and stderr for container names
        output = stdout + stderr
        logger.info("Extracting container names from output...")

        # Find all matches of container names with the specified statuses (Started/Healthy)
        matches = container_name_pattern.findall(output)

        if matches:
            # Extract unique container names
            container_names = list({match[0] for match in matches})  # Use a set to ensure uniqueness
            logger.info(f"Container names extracted: {container_names}")
            return container_names
        else:
            logger.warning("No container names found in the output.")
            return []