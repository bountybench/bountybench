import logging

import docker
from docker.models.containers import Container

from resources.base_resource import BaseResource

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Constants
ENTRYPOINT = "/bin/bash"


class DockerResource(BaseResource):
    """Docker Resource"""

    def __init__(self):
        self.client = docker.from_env()

    def execute(
        self, docker_image: str, name: str, command: str, network: str = None, work_dir: str = None, volumes: dict = None, detach: bool = True
    ) -> bool:
        """Run a Docker container with the specified configuration."""
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
        self.client.close()

    def stream_logs(self, container: Container, prefix: str = "") -> None:
        """Stream logs from the specified Docker container."""
        try:
            for line in container.logs(stdout=True, stderr=True, stream=True):
                logs = line.decode().strip()
                logger.info(f"{prefix}: {logs}")
        except Exception as e:
            logger.error(f"Error streaming logs: {e}")
