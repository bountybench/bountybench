import re
import time
from abc import ABC, abstractmethod
from pathlib import Path
from queue import Queue
from typing import List, Optional

from resources.base_resource import BaseResource
from resources.utils import run_command
from utils.logger import get_main_logger
from utils.progress_logger import start_progress, stop_progress

logger = get_main_logger(__name__)


class BaseSetupResource(BaseResource, ABC):
    """Base class for setup resources with common functionality."""

    def __init__(self, resource_id: str, config):
        super().__init__(resource_id, config)
        
        # Initialize container management
        self.container_names: List[str] = []
        self.health_check_timeout = 120
        self.work_dir = None  

    def fix_script_format(self, script_path: Path) -> None:
        """Fix common script formatting issues."""
        if not script_path.exists():
            return

        # Read the content of the script
        content = script_path.read_bytes()

        # Convert CRLF to LF if present
        content = content.replace(b"\r\n", b"\n")

        # Ensure there's a shebang line if missing
        if not content.startswith(b"#!"):
            content = b"#!/bin/bash\n" + content

        # Write the fixed content back
        script_path.write_bytes(content)

        # Make the script executable
        script_path.chmod(0o755)

    @abstractmethod
    def _start(self) -> None:
        """Start the environment by running the appropriate setup script. To be implemented by subclasses."""
        pass

    def restart(self) -> None:
        """Restart the environment by stopping and then starting it again."""
        self.stop()
        self._start()

    def stop(self) -> None:
        """Stop the environment by using docker compose down."""
        if not self.work_dir:
            logger.error("work_dir is not set, cannot stop environment")
            return
            
        docker_compose_file = self.work_dir / "docker-compose.yml"

        if docker_compose_file.exists():
            logger.info(f"Stopping docker in {self.work_dir}")
            try:
                run_command(
                    command=["docker", "compose", "down", "-v"], work_dir=str(self.work_dir)
                )
                logger.info(f"Stopped environment at {self.resource_id}.")
            except Exception as e:
                logger.error(
                    f"Unable to stop environment at {self.resource_id}: {e}",
                    exc_info=True,
                )

    def wait_until_all_containers_healthy(
        self, timeout: int = 300, check_interval: int = 2
    ) -> bool:
        """
        Wait until all Docker containers are healthy.
        :param timeout: The maximum time in seconds to wait for containers to become healthy.
        :param check_interval: The interval in seconds between health checks.
        :return: True if all containers are healthy before the timeout, otherwise raises TimeoutError.
        """
        if not self.container_names:
            logger.error("No container names available for health check.")
            raise ValueError("No container names available for health check.")

        container_queue = Queue()
        for container in self.container_names:
            container_queue.put(container)

        start_time = time.time()

        start_progress("Checking container health")

        try:
            while not container_queue.empty():
                container = container_queue.queue[0]

                inspect_result = run_command(
                    command=[
                        "docker",
                        "inspect",
                        "--format={{json .State.Health.Status}}",
                        container,
                    ]
                )
                health_status = inspect_result.stdout.strip().strip("'\"")

                if health_status == "healthy":
                    logger.info(f"Container '{container}' is healthy.")
                    container_queue.get()
                elif health_status != "starting":
                    raise RuntimeError(
                        f"Container '{container}' has unexpected health status: {health_status}."
                    )

                if time.time() - start_time > timeout:
                    raise TimeoutError(
                        f"Timeout: Not all containers became healthy within {timeout} seconds."
                    )

                time.sleep(check_interval)

            logger.info("All containers are healthy.")
            return True
        except Exception as e:
            raise
        finally:
            stop_progress()

    def extract_container_names(
        self, stdout: Optional[str] = None, stderr: Optional[str] = None
    ) -> List[str]:
        """
        Extract the names of all running containers from the setup scripts' output.
        Looks for lines matching the pattern: "Container <name> (Started|Healthy)".
        """
        container_name_pattern = re.compile(r"Container\s+([^\s]+)\s+(Started|Healthy)")

        # Ensure both stdout and stderr are strings
        stdout = stdout.decode("utf-8") if isinstance(stdout, bytes) else (stdout or "")
        stderr = stderr.decode("utf-8") if isinstance(stderr, bytes) else (stderr or "")

        output = stdout + stderr
        matches = container_name_pattern.findall(output)

        if matches:
            container_names = list({match[0] for match in matches})
            logger.info(f"Container names extracted: {container_names}")
            return container_names
        else:
            return []

    def save_to_file(self, filepath: Path) -> None:
        """
        Saves the resource state to a JSON file.
        """
        import json

        state = self.to_dict()
        filepath.write_text(json.dumps(state, indent=2))

    @classmethod
    def load_from_file(cls, filepath: Path, **kwargs) -> "BaseSetupResource":
        """
        Loads a resource state from a JSON file.
        """
        import json

        data = json.loads(filepath.read_text())
        return cls.from_dict(data, **kwargs)