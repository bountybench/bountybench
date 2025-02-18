import atexit
import json
import os
import sys
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
from utils.progress_logger import start_progress, stop_progress

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
        volumes = docker_message.volumes

        output, exit_code = self.execute(docker_image, command, network, volumes=volumes)

        return ActionMessage(
            resource_id=self.resource_id,
            message=f"Execution completed with exit code {exit_code}. Output:\n{output}",
            additional_metadata={
                "docker_image": docker_image,
                "command": command,
                "exit_code": exit_code,
                "output": output,
                "success": (exit_code == 0),
            },
            prev=docker_message
        )
    

    def execute(
        self,
        docker_image: str,
        command: str,
        network: str = None,
        work_dir: str = None,
        volumes: dict = None,
        detach: bool = False,
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

        Returns:
            tuple: A tuple containing the logs from the container and the exit code.
        """

        unique_name = f"{self.resource_id}-{uuid.uuid4().hex[:10]}"
        start_progress(f"Running command in Docker: {command}")
        try:
            # If command is a string, convert it to a list
            if isinstance(command, str):
                command = ["/bin/bash", "-c", command]

            container = self.client.containers.run(
                image=docker_image,
                command=command,  # Pass command directly without additional formatting
                volumes=volumes,
                network=network,
                working_dir=work_dir,
                detach=True,
                name=unique_name,
            )

            logs = ""
            last_line = ""
            for line in container.logs(stdout=True, stderr=True, stream=True):
                decoded_line = line.decode().strip()
                logs += decoded_line + "\n"
                if decoded_line:  # Only update last_line if non-empty
                    last_line = decoded_line

            # Wait for the container to finish and get the exit code
            result = container.wait()
            exit_code = result["StatusCode"]

            logger.info(f"Container logs:\n{logs.strip()}")
            logger.info(f"Exit code: {exit_code}")

            return last_line, exit_code

        except docker.errors.APIError as e:
            logger.error(f"Docker API error: {str(e)}")
            return str(e), -1
        except Exception as e:
            logger.error(f"Error running Docker container: {e}")
            return str(e), -1
        finally:
            stop_progress()
            try:
                container.remove(force=True)
            except:
                pass  # If container removal fails, just ignore it

    def copy_from_container(
        self, container_name: str, source_path: str, dest_path: str
    ) -> None:
        """
        Copy a file or directory from a container to the host system.

        Args:
            container_name (str): The name of the container to copy from.
            source_path (str): The path of the file or directory in the container.
            dest_path (str): The destination path on the host system.
        """
        try:
            container = self.client.containers.get(container_name)

            # Get file/directory data from container
            bits, stat = container.get_archive(source_path)

            # Ensure the destination directory exists
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            # Write the file/directory data to the destination
            with open(dest_path, "wb") as f:
                for chunk in bits:
                    f.write(chunk)

            logger.info(
                f"Copied from container {container_name}: {source_path} -> {dest_path}"
            )
        except docker.errors.NotFound:
            logger.critical(f"Container not found: {container_name}")
            sys.exit(1)
        except docker.errors.APIError as e:
            logger.error(f"Docker API error while copying: {str(e)}")
        except Exception as e:
            logger.error(f"Error copying from container: {e}")

    def stop(self) -> None:
        """
        Stop the Docker client by closing the connection.
        """
        self.client.close()

    def handle_docker_exception(self, e: DockerException) -> RuntimeError:
        """Handle different Docker exceptions for clearer debugging and return appropriate runtime error."""
        error_message = ""

        if isinstance(e, APIError):
            error_message = "Docker API error: " + str(e)
        elif isinstance(e, NotFound):
            error_message = "Not found error in Docker: " + str(e)
        elif isinstance(e, ImageNotFound):
            error_message = "Image not found: " + str(e)
        elif isinstance(e, ContainerError):
            error_message = "Container error: " + str(e)
        elif isinstance(e, BuildError):
            error_message = "Build error: " + str(e)
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
        }

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> "DockerResource":
        """
        Creates a DockerResource instance from a serialized dictionary.
        """
        return cls(name=data["resource_id"])

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
