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
        Raises an exception if the timeout is reached before all containers are healthy.
        """
        container_names = self.extract_container_names()

        if not container_names:
            logger.error("No container names available for health check.")
            sys.exit(1)

        logger.info(f"Waiting for all containers to become healthy...")

        start_time = time.time()

        while True:
            all_healthy = True

            for container in container_names:
                try:
                    # Check health status of each container
                    logger.info(f"Checking health of container {container}")
                    inspect_result = run_command(
                        command=[
                            "docker", "inspect", "--format={{json .State.Health.Status}}", container]
                    )
                    health_status = inspect_result.stdout.strip().strip("'\"")

                    if health_status == "healthy":
                        logger.info(f"Container '{container}' is healthy.")
                    elif health_status in ["starting"]:
                        logger.info(
                            f"Container '{container}' health status: {health_status}. Waiting..."
                        )
                        all_healthy = False
                    else:
                        logger.warning(
                            f"Container '{container}' has unexpected health status: {health_status}."
                        )
                        sys.exit(1)

                except Exception as e:
                    logger.error(f"Unexpected error while checking health status of container '{container}': {e}")
                    sys.exit(1)

            if all_healthy:
                logger.info("All containers are healthy.")
                break

            if time.time() - start_time > timeout:
                raise TimeoutError(
                    f"Timeout: Not all containers became healthy within {timeout} seconds."
                )

            time.sleep(check_interval)

    def extract_container_names(self):
        """
        Extract the names of all running containers.
        """
        try:
            # Use the run_command wrapper to execute 'docker ps' and extract container names
            result = run_command(["docker", "ps", "--format", "{{.Names}}"])
            # Split result by newlines to get individual container names
            container_names = result.stdout.strip().split("\n")
            return container_names
        except Exception as e:
            logger.error(f"Error extracting container names: {e}")
            return []