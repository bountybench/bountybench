import atexit
import os
import re
import time
from queue import Queue
from typing import List, Optional

from resources.base_resource import BaseResource
from resources.utils import run_command
from utils.logger import get_main_logger
from utils.progress_logger import start_progress, stop_progress

from dataclasses import dataclass
from typing import Optional
import os
from resources.base_resource import BaseResourceConfig


logger = get_main_logger(__name__)


@dataclass
class SetupResourceConfig(BaseResourceConfig):
    """Configuration for SetupResource"""
    task_level_setup: bool
    task_dir: str
    files_dir: str
    bounty_number: Optional[str] = None
    server_address: Optional[str] = None

    def validate(self) -> None:
        """Validate Setup configuration"""
        if not os.path.exists(self.task_dir):
            raise ValueError(f"Invalid task_dir: {self.task_dir}")
        if self.server_address and ":" not in self.server_address:
            raise ValueError(f"Invalid server_address format: {self.server_address}")
        

class SetupResource(BaseResource):
    """SetupResource for initializing and managing containers."""

    def __init__(self, resource_id: str, config: SetupResourceConfig):
        # Call the superclass constructor first
        super().__init__(resource_id, config)

        self.task_dir = str(self._resource_config.task_dir)
        self.files_dir = self._resource_config.files_dir


        # Access the configuration
        self.task_level_setup = self._resource_config.task_level_setup
        self.role = "task_server" if self.task_level_setup else "repo_resource"

        # Handle server address if provided (task_server only)
        if self.task_level_setup:
            if not self._resource_config.server_address:
                raise ValueError("Server address is required for task_server setup.")
            self.host_name, self.port_number = self.parse_server_address(
                self._resource_config.server_address
            )
            if not self._resource_config.bounty_number:
                raise ValueError("Bounty number is required for task_server setup.")
            self.bounty_dir = os.path.join(
                self.task_dir,
                "bounties",
                f"bounty_{self._resource_config.bounty_number}",
            )
        else:
            self.host_name, self.port_number = None, None
            self.bounty_dir = None


        # Initialize container management
        self.container_names: List[str] = []
        self.health_check_timeout = 120

        self._start()
        atexit.register(self.stop)

    def parse_server_address(self, server_address: str) -> (str, str):
        """Parse the server address and return host and port."""
        if not server_address: 
            return None, None
        try:
            host_name, port_number = server_address.split(":")
            return host_name, port_number
        except ValueError:
            logger.error(f"Invalid server_address format: {server_address}. Expected format: hostname:port")
            raise ValueError("Invalid server_address format.")

    def _start(self) -> None:
        """Start the environment by running the appropriate setup script."""
        setup_script = "setup_bounty_env.sh" if self.task_level_setup else "setup_repo_env.sh"
        work_dir = (
            os.path.join(self.bounty_dir, "setup_files")
            if self.task_level_setup
            else self.task_dir
        )

        if not os.path.exists(work_dir):
            raise FileNotFoundError(f"Work directory does not exist: {work_dir}")

        try:
            start_progress(f"Executing {setup_script} in {work_dir}")
            try:
                result = run_command(command=[f"./{setup_script}"], work_dir=work_dir)
            finally:
                stop_progress()
            logger.info(f"Environment setup complete for {self.resource_id}")
            self.container_names = self.extract_container_names(result.stdout, result.stderr)

            if self.container_names:
                self.wait_until_all_containers_healthy()

        except FileNotFoundError:
            logger.error(f"Setup script not found: {os.path.join(work_dir, setup_script)}")
            raise
        except Exception as e:
            logger.error(f"Unable to set up environment at {self.resource_id}: {e}")
            raise

    def restart(self) -> None:
        """Restart the environment by stopping and then starting it again."""
        self.stop()
        self._start()
        
    def stop(self) -> None:
        """Stop the environment by running 'stop_docker.sh'."""
        work_dir = os.path.join(self.bounty_dir, "setup_files") if self.task_level_setup else self.task_dir
        docker_compose_file = os.path.join(work_dir, "docker-compose.yml")


        if os.path.exists(docker_compose_file): 
            logger.info(f"Stopping docker in {work_dir}")
            try:
                run_command(command=["docker", "compose", "down", "-v"], work_dir=work_dir)
                logger.info(f"Stopped environment at {self.resource_id}.")
            except Exception as e:
                logger.error(f"Unable to stop environment at {self.resource_id}: {e}", exc_info=True)


    def wait_until_all_containers_healthy(self, timeout: int = 300, check_interval: int = 2) -> bool:
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

                inspect_result = run_command(command=["docker", "inspect", "--format={{json .State.Health.Status}}", container])
                health_status = inspect_result.stdout.strip().strip("'\"")

                if health_status == "healthy":
                    logger.info(f"Container '{container}' is healthy.")
                    container_queue.get()
                elif health_status != "starting":
                    raise RuntimeError(f"Container '{container}' has unexpected health status: {health_status}.")

                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Timeout: Not all containers became healthy within {timeout} seconds.")

                time.sleep(check_interval)

            logger.info("All containers are healthy.")
            return True

        finally:
            stop_progress()

    def extract_container_names(self, stdout: Optional[str] = None, stderr: Optional[str] = None) -> List[str]:
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
            logger.warning("No container names found in the output.")
            return []

    def to_dict(self) -> dict:
        """
        Serializes the SetupResource state to a dictionary.
        """
        return {
            'task_level_setup': self.task_level_setup,
            'task_dir': self.task_dir,
            'files_dir': self.files_dir,
            'bounty_dir': self.bounty_dir,
            'host_name': self.host_name,
            'port_number': self.port_number,
            'resource_id': self.resource_id,
            'role': self.role,
            'container_names': self.container_names,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S%z')
        }

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> 'SetupResource':
        """
        Creates a SetupResource instance from a serialized dictionary.
        """
        bounty_number = os.path.basename(data['bounty_dir']).replace('bounty_', '')
        server_address = f"{data['host_name']}:{data['port_number']}" if data['host_name'] and data['port_number'] else None
        
        instance = cls(
            task_level_setup=data['task_level_setup'],
            task_dir=data['task_dir'],
            files_dir=data['files_dir'],
            bounty_number=bounty_number,
            server_address=server_address
        )
        instance.container_names = data['container_names']
        return instance

    def save_to_file(self, filepath: str) -> None:
        """
        Saves the resource state to a JSON file.
        """
        import json
        state = self.to_dict()
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str, **kwargs) -> 'SetupResource':
        """
        Loads a resource state from a JSON file.
        """
        import json
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data, **kwargs)