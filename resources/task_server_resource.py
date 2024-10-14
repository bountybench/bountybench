import atexit
import logging
import sys
import time

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
        self.healthy_check_timeout = 120
        self.start()

        resource_dict[self.resource_id] = self
        atexit.register(self.stop)

    def start(self) -> None:
        try:
            result = run_command(
                command=["./start_docker.sh"],
                work_dir=str(self.task_repo_dir),
            )

            logger.info(f"Spun up task server at {self.resource_id}")
            self.wait_until_healthy()
        except Exception as e:
            # Handle errors
            logger.info(
                f"Unable to spin up task server at {self.resource_id}.")

    def stop(self) -> None:
        try:
            result = run_command(
                command=["./stop_docker.sh"],
                work_dir=str(self.task_repo_dir),
            )
            # Print the output
            logger.info(f"Stop task server at {self.resource_id}.")
        except Exception as e:
            # Handle errors
            logger.info(
                f"Unable to stop task server at {self.resource_id}. Here is error:", e.stderr)

    def wait_until_healthy(self) -> None:
        """
        Wait until the Docker container's health status is 'healthy'.
        Raises an exception if the timeout is reached before the container is healthy.
        """
        logger.info(
            f"Waiting for server '{self.host_name}' to become healthy...")
        start_time = time.time()
        while True:
            try:
                inspect_result = run_command(
                    command=[
                        "docker", "inspect", "--format='{{json .State.Health.Status}}'", self.host_name],
                    work_dir=str(self.task_repo_dir),
                )
                # The output includes quotes, e.g., '"healthy"'
                health_status = inspect_result.stdout.strip().strip("'\"")

                if health_status == "healthy":
                    logger.info(f"Container '{self.host_name}' is healthy.")
                    break
                elif health_status in ["starting"]:
                    logger.info(
                        f"Container '{self.host_name}' health status: {health_status}. Waiting...")
                else:
                    logger.warning(
                        f"Container '{self.host_name}' has unexpected health status: {health_status}.")
                    sys.exit(1)
            except Exception as e:
                logger.error(
                    f"Unexpected error while checking health status: {e}")

            if time.time() - start_time > self.health_check_timeout:
                raise TimeoutError(
                    f"Timeout: Container '{self.host_name}' did not become healthy within {self.health_check_timeout} seconds.")

            time.sleep(2)
