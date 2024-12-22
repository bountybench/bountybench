import atexit
import uuid
import docker

from resources.base_resource import BaseResource
from resources.resource_dict import resource_dict
from utils.workflow_logger import workflow_logger
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

# Constants
ENTRYPOINT = "/bin/bash"

class DockerResource(BaseResource):
    """
    Docker Resource to manage Docker containers.
    """

    def __init__(self, name: str):
        """
        Initialize Docker client from environment.
        """
        self.client = docker.from_env()
        self.resource_id = name
        workflow_logger.add_resource(f"DockerResource: {self.resource_id}")
        resource_dict[self.resource_id] = self
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

    def stop(self) -> None:
        """
        Stop the Docker client by closing the connection.
        """
        self.client.close()