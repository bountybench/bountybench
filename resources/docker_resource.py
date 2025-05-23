import atexit
import json
import threading
import time
import uuid
from dataclasses import dataclass

import docker
from docker.errors import (
    APIError,
    BuildError,
    ContainerError,
    DockerException,
    ImageNotFound,
    NotFound,
)

from messages.action_messages.docker_action_message import DockerActionMessage
from resources.base_resource import ActionMessage, BaseResourceConfig
from resources.runnable_base_resource import RunnableBaseResource
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

# Constants
ENTRYPOINT = "/bin/bash"


@dataclass
class DockerResourceConfig(BaseResourceConfig):
    """Configuration for DockerResource"""

    def validate(self) -> None:
        """Validate Docker configuration"""
        pass


class DockerResource(RunnableBaseResource):
    """
    Docker Resource to manage Docker containers.
    """

    def __init__(self, resource_id: str, config: DockerResourceConfig):
        super().__init__(resource_id, config)

        try:
            self.client = docker.from_env()
        except FileNotFoundError as e:
            raise RuntimeError("Docker daemon not available: " + str(e)) from e
        except DockerException as e:
            self.handle_docker_exception(e)
        except Exception as e:
            raise RuntimeError(
                "Unexpected error while initializing Docker client: " + str(e)
            ) from e

        atexit.register(self.stop)

    async def run(self, docker_message: DockerActionMessage) -> ActionMessage:
        """Execute a command inside Docker using DockerActionMessage."""

        docker_image = docker_message.docker_image
        command = docker_message.command
        network = docker_message.network
        work_dir = docker_message.work_dir
        volumes = docker_message.volumes

        output, exit_code = self.execute(
            docker_image=docker_image,
            command=command,
            network=network,
            work_dir=work_dir,
            volumes=volumes,
        )

        docker_message.set_message(output)
        docker_message.set_exit_code(exit_code)
        return docker_message

    def execute(
        self,
        docker_image: str,
        command: str,
        network: str = None,
        work_dir: str = None,
        volumes: dict = None,
        detach: bool = False,
        timeout: int = 600,  # timeout in seconds (default: 10 minutes)
    ) -> tuple:
        """
        Run a Docker container with the specified configuration.

        Args:
            docker_image (str): The Docker image to run.
            command (str): The command to execute inside the container.
            network (Optional[str]): The Docker network to attach the container to.
            work_dir (Optional[str]): The working directory inside the container.
            volumes (Optional[dict]): The volumes to mount in the container.
            detach (bool): Run the container in detached mode. Defaults to False.
            timeout (int): Time in seconds before killing the container. Defaults to 600.

        Returns:
            tuple: A tuple containing the logs from the container and the exit code.
        """

        unique_name = f"{self.resource_id}-{uuid.uuid4().hex[:10]}"

        def stream_logs(container, logs, stop_event):
            try:
                for line in container.logs(stdout=True, stderr=True, stream=True):
                    if stop_event.is_set():
                        break
                    decoded_line = line.decode().strip()
                    print(decoded_line)
                    logs.append(decoded_line)
            except Exception as e:
                logger.warning(f"Log stream ended: {e}")

        logger.info(f"Running command in Docker: {command}")
        try:
            container = self.client.containers.run(
                image=docker_image,
                command=command,  # Pass command directly without additional formatting
                volumes=volumes,
                network=network,
                working_dir=work_dir,
                detach=True,
                name=unique_name,
            )

            logger.info("Container started. Streaming logs...")

            # Thread-safe way to enable real-time logging while preventing hanging
            logs = []
            stop_event = threading.Event()
            log_thread = threading.Thread(
                target=stream_logs, args=(container, logs, stop_event)
            )
            log_thread.start()

            start_time = time.time()
            while container.status != "exited":
                container.reload()
                if time.time() - start_time > timeout:
                    logger.warning(f"Container timed out after {timeout} seconds.")
                    container.kill()
                    logs.append(f"Timeout after {timeout} seconds.")
                    exit_code = -1
                    break
                time.sleep(5)
            else:
                result = container.wait()
                exit_code = result.get("StatusCode", -1)

            stop_event.set()
            log_thread.join(timeout=5)

            logger.info(f"Exit code: {exit_code}")
            return "\n".join(logs), exit_code

        except docker.errors.APIError as e:
            logger.error(f"Docker API error: {e}")
            return str(e), -1
        except Exception as e:
            logger.error(f"Error running Docker container: {e}")
            return str(e), -1
        finally:
            try:
                container.remove(force=True)
            except:
                pass  # If container removal fails, just ignore it

    def stop(self) -> None:
        """
        Stop the Docker client by closing the connection.
        """
        self.client.close()

    def handle_docker_exception(self, e: DockerException) -> RuntimeError:
        """Handle different Docker exceptions for clearer debugging and return appropriate runtime error."""
        error_message = ""

        if isinstance(e, ImageNotFound):
            error_message = "Image not found: " + str(e)
        elif isinstance(e, NotFound):
            error_message = "Not found error in Docker: " + str(e)
        elif isinstance(e, ContainerError):
            error_message = "Container error: " + str(e)
        elif isinstance(e, BuildError):
            error_message = "Build error: " + str(e)
        elif isinstance(e, APIError):
            error_message = "Docker API error: " + str(e)
        else:
            error_message = "Error while connecting to Docker: " + str(e)

        return RuntimeError(error_message)

    def to_dict(self) -> dict:
        """
        Serializes the DockerResource state to a dictionary.
        """
        return {
            "resource_id": self.resource_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "config": self._resource_config.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> "DockerResource":
        """
        Creates a DockerResource instance from a serialized dictionary.
        """
        return cls(resource_id=data["resource_id"], config=data["config"])

    def save_to_file(self, filepath: str) -> None:
        """
        Saves the resource state to a JSON file.
        """
        state = self.to_dict()
        with open(filepath, "w") as f:
            json.dump(state, f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str, **kwargs) -> "DockerResource":
        """
        Loads a resource state from a JSON file.
        """
        with open(filepath, "r") as f:
            data = json.load(f)
        return cls.from_dict(data, **kwargs)
