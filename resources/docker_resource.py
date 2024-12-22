import atexit

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
        self, docker_image: str, command: str, network: str = None, work_dir: str = None, volumes: dict = None, detach: bool = True
    ) -> str:
        """
        Run a Docker container with the specified configuration.

        Args:
            docker_image (str): The Docker image to run.
            command (str): The command to execute inside the container.
            network (Optional[str]): The Docker network to attach the container to.
            work_dir (Optional[str]): The working directory inside the container.
            volumes (Optional[dict]): The volumes to mount in the container.
            detach (bool): Run the container in detached mode. Defaults to True.

        Returns:
            str: The logs from the container.
        """
        logger.info(
            f"Running command in Docker: {command}, Work Dir: {work_dir}")
        container = self.client.containers.run(
            image=docker_image,
            command=f'-c "{command}"',
            volumes=volumes,
            network=network,
            entrypoint=ENTRYPOINT,
            working_dir=work_dir,
            detach=detach,
            name=self.resource_id,
        )
        logs = ""
        last_line = ""
        try:
            for line in container.logs(stdout=True, stderr=True, stream=True):
                logs += (line.decode().strip() + "\n")
                last_line = line.decode().strip()
            container.remove()
            logger.info(f"Exploit logs:{logs}")
            return last_line
        except Exception as e:
            logger.error(f"Error streaming logs: {e}")
            return logs

    def stop(self) -> None:
        """
        Stop the Docker client by closing the connection.
        """
        self.client.close()
