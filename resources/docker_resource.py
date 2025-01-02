import atexit
import uuid
import docker
import os
from pathlib import Path
import time
import json

from resources.base_resource import BaseResource
from resources.resource_dict import resource_dict
from utils.workflow_logger import workflow_logger
from utils.logger import get_main_logger
from dataclasses import dataclass
from typing import Optional
from resources.base_resource import BaseResourceConfig


logger = get_main_logger(__name__)

# Constants
ENTRYPOINT = "/bin/bash"


@dataclass
class DockerResourceConfig(BaseResourceConfig):
    """Configuration for DockerResource"""

    def validate(self) -> None:
        """Validate Docker configuration"""
        pass


class DockerResource(BaseResource):
    """
    Docker Resource to manage Docker containers.
    """

    def __init__(self, resource_id: str, config: DockerResourceConfig):
        super().__init__(resource_id, config)
        
        self.client = docker.from_env()
        atexit.register(self.stop)

    def execute(
        self, docker_image: str, command: str, network: str = None, work_dir: str = None, volumes: dict = None, detach: bool = False
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
        
        logger.info(f"Running command in Docker: {command}, Work Dir: {work_dir}")
        try:
            # If command is a string, convert it to a list
            if isinstance(command, str):
                command = ['/bin/bash', '-c', command]
                
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
                logs += (decoded_line + "\n")
                if decoded_line:  # Only update last_line if non-empty
                    last_line = decoded_line
            
            # Wait for the container to finish and get the exit code
            result = container.wait()
            exit_code = result['StatusCode']
            
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
            try:
                container.remove(force=True)
            except:
                pass  # If container removal fails, just ignore it

    def copy_from_container(self, container_name: str, source_path: str, dest_path: str) -> None:
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
            with open(dest_path, 'wb') as f:
                for chunk in bits:
                    f.write(chunk)
            
            logger.info(f"Copied from container {container_name}: {source_path} -> {dest_path}")
        except docker.errors.NotFound:
            logger.error(f"Container not found: {container_name}")
        except docker.errors.APIError as e:
            logger.error(f"Docker API error while copying: {str(e)}")
        except Exception as e:
            logger.error(f"Error copying from container: {e}")

    def stop(self) -> None:
        """
        Stop the Docker client by closing the connection.
        """
        self.client.close()

    def to_dict(self) -> dict:
        """
        Serializes the DockerResource state to a dictionary.
        """
        return {
            'resource_id': self.resource_id,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S%z')
        }

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> 'DockerResource':
        """
        Creates a DockerResource instance from a serialized dictionary.
        """
        return cls(name=data['resource_id'])

    def save_to_file(self, filepath: str) -> None:
        """
        Saves the resource state to a JSON file.
        """
        state = self.to_dict()
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str, **kwargs) -> 'DockerResource':
        """
        Loads a resource state from a JSON file.
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data, **kwargs)