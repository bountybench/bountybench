import atexit
import logging
import os
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
        self.health_check_timeout = 120
        self.container_name = None
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
            # Extract the container name from stdout or stderr
            self.container_name = self.extract_container_name(result.stdout, result.stderr)
            if not self.container_name:
                raise Exception(f"Failed to retrieve container name for {self.host_name}")
            logger.info(f"Using container '{self.container_name}' for health checks.")
        except Exception as e:
            # Handle errors
            logger.error(
                f"Unable to spin up task server at {self.resource_id}.")
            sys.exit(1)
        finally:
            # Return to the previous directory to ensure no side effects
            os.chdir('..')

        self.wait_until_healthy()

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

    def wait_until_healthy(self) -> None:
        """
        Wait until the Docker container's health status is 'healthy'.
        Raises an exception if the timeout is reached before the container is healthy.
        """        
        if not self.container_name:
            logger.error("No container name available for health check.")
            sys.exit(1)

        logger.info(
            f"Waiting for server '{self.container_name}' to become healthy...")
        start_time = time.time()
        while True:
            try:
                inspect_result = run_command(
                    command=[
                        "docker", "inspect", "--format='{{json .State.Health.Status}}'", self.container_name],
                    work_dir=str(self.task_repo_dir),
                )
                # The output includes quotes, e.g., '"healthy"'
                health_status = inspect_result.stdout.strip().strip("'\"")

                if health_status == "healthy":
                    logger.info(f"Container '{self.container_name}' is healthy.")
                    break
                elif health_status in ["starting"]:
                    logger.info(
                        f"Container '{self.container_name}' health status: {health_status}. Waiting...")
                else:
                    logger.warning(
                        f"Container '{self.container_name}' has unexpected health status: {health_status}.")
                    sys.exit(1)
            except Exception as e:
                logger.error(
                    f"Unexpected error while checking health status: {e}")

            if time.time() - start_time > self.health_check_timeout:
                raise TimeoutError(
                    f"Timeout: Container '{self.container_name}' did not become healthy within {self.health_check_timeout} seconds.")

            time.sleep(2)

    def extract_container_name(self, stdout: str, stderr: str) -> str:
        """
        Extract the container name from the output of start_docker.sh (stdout or stderr).
        This assumes that the container name appears in a recognizable format.

        Args:
            stdout (str): The stdout output from running the start script.
            stderr (str): The stderr output from running the start script.

        Returns:
            str: The extracted container name, or None if no name could be found.
        """
        # This pattern matches "Container <name> <status>"
        container_name_pattern = re.compile(r"Container\s+([^\s]+)\s+Started")

        # Ensure both stdout and stderr are strings
        if stdout is None:
            stdout = ""
        if stderr is None:
            stderr = ""

        if not isinstance(stdout, str):
            stdout = stdout.decode("utf-8") if isinstance(stdout, bytes) else ""
        if not isinstance(stderr, str):
            stderr = stderr.decode("utf-8") if isinstance(stderr, bytes) else ""

        # Search in both stdout and stderr for the container name
        output = stdout + stderr
        logger.info("Extracting container name from output...")

        match = container_name_pattern.search(output)
        
        if match:
            container_name = match.group(1)
            logger.info(f"Container name extracted: {container_name}")
            return container_name
        else:
            logger.warning("No container name found in the output.")
            return None