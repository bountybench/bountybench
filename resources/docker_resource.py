import logging

import docker
from docker.models.containers import Container

from resources.base_resource import BaseResource

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
ENTRYPOINT = "/bin/bash"


class DockerResource(BaseResource):
    """
    Docker Resource to manage Docker containers.
    """

    def __init__(self):
        """
        Initialize Docker client from environment.
        """
        self.client = docker.from_env()

    def execute(
        self, docker_image: str, name: str, command: str, network: str = None, work_dir: str = None, volumes: dict = None, detach: bool = True
    ) -> str:
        """
        Run a Docker container with the specified configuration.

        Args:
            docker_image (str): The Docker image to run.
            name (str): The name of the container.
            command (str): The command to execute inside the container.
            network (Optional[str]): The Docker network to attach the container to.
            work_dir (Optional[str]): The working directory inside the container.
            volumes (Optional[dict]): The volumes to mount in the container.
            detach (bool): Run the container in detached mode. Defaults to True.

        Returns:
            str: The logs from the container.
        """
        logger.info(f"Running command in Docker: {command}, Work Dir: {work_dir}")
        container = self.client.containers.run(
            image=docker_image,
            command=f'-c "{command}"',
            volumes=volumes,
            network=network,
            entrypoint=ENTRYPOINT,
            working_dir=work_dir,
            detach=detach,
            name=name,
        )
        logs = ""
        try:
            for line in container.logs(stdout=True, stderr=True, stream=True):
                logs += line.decode().strip()
            container.remove()
            return logs
        except Exception as e:
            logger.error(f"Error streaming logs: {e}")
            return logs

    def stop(self) -> None:
        """
        Stop the Docker client by closing the connection.
        """
        self.client.close()