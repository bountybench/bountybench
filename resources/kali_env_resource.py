import atexit
import os
import sys
import time
from typing import Dict, Optional, Tuple

import docker
from docker.models.containers import Container

from resources.base_resource import BaseResource
from resources.utils import get_stdout_text
from utils.workflow_logger import workflow_logger
from utils.logger import get_main_logger
from utils.progress_logger import start_progress, stop_progress
from dataclasses import dataclass
from typing import Dict, Optional
import os
from resources.base_resource import BaseResourceConfig


# Configure logging
logger = get_main_logger(__name__)

import signal
from contextlib import contextmanager

@contextmanager
def timeout_context(seconds):
    def signal_handler(signum, frame):
        raise TimeoutError("Timed out!")
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        
# Constants with type annotations
DOCKER_IMAGE: str = "cybench/bountyagent:latest"
ENTRYPOINT: str = "/usr/local/bin/dockerd-entrypoint.sh"

MAX_RETRIES = 3
RETRY_DELAY = 10


@dataclass
class KaliEnvResourceConfig(BaseResourceConfig):
    """Configuration for KaliEnvResource"""
    task_dir: Optional[str] = None
    bounty_number: Optional[str] = None
    volumes: Optional[Dict[str, Dict[str, str]]] = None
    target_host: Optional[str] = None

    def validate(self) -> None:
        """Validate KaliEnv configuration"""
        if self.task_dir and not os.path.exists(self.task_dir):
            raise ValueError(f"Invalid task_dir: {self.task_dir}")
        if self.volumes:
            for host_path in self.volumes.keys():
                parent_dir = os.path.dirname(host_path)
                if not os.path.exists(parent_dir):
                    raise ValueError(f"Invalid volume host path parent directory: {parent_dir}")

                
class KaliEnvResource(BaseResource):
    """Kali Linux Environment Resource"""

    def __init__(self, resource_id: str, config: KaliEnvResourceConfig):
        super().__init__(resource_id, config)
        
        self.client = docker.from_env()
        self.container = self._start(self.resource_id, self._resource_config.volumes)

        self.target_host = self._resource_config.target_host
        
        # Initialize bounty directory if task_dir and bounty_number provided
        if self._resource_config.task_dir and self._resource_config.bounty_number:
            self.bounty_dir = os.path.join(
                str(self._resource_config.task_dir),
                "bounties",
                f"bounty_{self._resource_config.bounty_number}"
            )
        
        if self.target_host:
            self.connect_to_target_hosts_check(self.target_host)

        atexit.register(self.stop)
    
    def _start(self, name: str, volumes: Optional[Dict[str, Dict[str, str]]]) -> Container:
        """
        Start a Kali Linux container to be used throughout the lifecycle.
        """
        for attempt in range(MAX_RETRIES):
            try:
                # Attempt to get existing container
                try:
                    container = self.client.containers.get(name)
                    logger.info(f"Container '{name}' already exists.")
                    if container.status != "running":
                        logger.info(f"Container '{name}' is not running. Removing it.")
                        container.remove(force=True)
                    else:
                        start_progress(f"Container '{name}' is running. Stopping and removing it.")
                        try:
                            container.stop()
                            container.remove()
                        finally:
                            stop_progress()
                except docker.errors.NotFound:
                    logger.info(f"No existing container named '{name}'.")

                start_progress(f"Starting a new Docker container (Attempt {attempt + 1}/{MAX_RETRIES})...")
                try:
                    container = self.client.containers.run(
                        image=DOCKER_IMAGE,
                        cgroupns="host",
                        network="shared_net",
                        volumes=volumes,
                        entrypoint=ENTRYPOINT,
                        detach=True,
                        name=name,
                    )
                    logger.info("KaliEnvResource Docker container started successfully.")
                finally:
                    stop_progress()

                container_info = self.client.api.inspect_container(container.id)
                mounts = container_info['Mounts']
                logger.debug(f"Container mounts: {mounts}")
                return container
            except docker.errors.APIError as e:
                logger.error(f"Docker API error while starting container: {e}")
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("Failed to start Docker container after maximum retries.")
                    sys.exit(1)
            except Exception as e:
                logger.error(f"Unexpected error while starting container: {e}")
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("Failed to start Docker container after maximum retries.")
                    sys.exit(1)

    def cleanup_tmp(self):
        cleanup_command = "rm -rf * .*"
        return self.run_command(cleanup_command, workdir="/app")
    
    def stop(self) -> None:
        """
        Stop and remove the Docker container when the program exits.

        This function is automatically registered to run when the program terminates.
        """
        if self.container:
            try:
                logger.info("Cleaning up: removing tmp files.")
                self.cleanup_tmp()
                logger.info("Cleaning up: stopping and removing Docker container.")
                self.container.stop()
                self.container.remove()
                self.container = None
                logger.info("Docker container cleaned up successfully.")
            except Exception as e:
                logger.error(f"Error cleaning up Docker container: {e}")

    def run_command(self, command: str, timeout: int = 120, workdir: Optional[str] = None, logging: bool = False, tty: bool = False) -> Tuple[str, str]:
        command_str = command
        if len(command) > 33:
            command_str = command[:30] + "..."
        start_progress(f"Running command in Docker container (workdir: {workdir}): {command_str}")
        try:
            with timeout_context(timeout):
                exec_id = self.client.api.exec_create(
                    container=self.container.id,
                    cmd=["/bin/bash", "-c", command],
                    workdir=workdir,
                    stdin=False,
                    stdout=True,
                    stderr=True,
                    tty=tty,
                )["Id"]

                output = self.client.api.exec_start(exec_id, stream=False, demux=True)
                stdout, stderr = output or (None, None)

            stdout_text = get_stdout_text(stdout)
            if tty:
                stdout_text = stdout_text.replace("\r", "")
            stderr_text = get_stdout_text(stderr)
            logger.info(f"Command executed successfully.\nstdout: {stdout_text}\nstderr: {stderr_text}")
            if logging:
                workflow_logger.log_action(action_name="kali", input_data=command, output_data={"stdout": stdout_text, "stderr": stderr_text}, metadata={})
            return stdout_text, stderr_text

        except TimeoutError:
            logger.warning(f"Command '{command}' timed out after {timeout} seconds.")
            # We can't stop the execution, but we can log that it timed out
            return f"Command '{command}' timed out after {timeout} seconds.", ""

        except docker.errors.APIError as e:
            logger.error(f"Docker API error while executing command: {e}")
            return "", f"Docker API error: {str(e)}"

        except Exception as e:
            logger.error(f"Unexpected error while executing command: {e}")
            return "", f"Unexpected error: {str(e)}"
        
        finally:
            stop_progress()

    def parse_target_host(self, target_host: str) -> Tuple[str, int]:
        """
        Parse the target host string into hostname and port.

        Args:
            target_host (str): The target host in the format hostname:port.

        Returns:
            Tuple[str, int]: A tuple containing the hostname and port as an integer.
        """
        try:
            hostname, port = target_host.split(":")
            return hostname, int(port)
        except ValueError:
            logger.error(
                f"Invalid target_host format: {target_host}. Expected format: hostname:port")
            sys.exit(1)

    def connect_to_target_hosts_check(self, target_hosts: str) -> None:
        """
        Checks if kali resource can connect on the specified target hosts with retries.

        Args:
            target_hosts (str): A string containing space-separated target hosts in the format hostname:port.
        """
        hosts = target_hosts.split()
        failed_hosts = []

        for target_host in hosts:
            hostname, port = self.parse_target_host(target_host)

            def nc_check():
                """
                Use netcat to check if the specified hostname and port are open.

                Returns:
                    bool: True if the port is open, False otherwise.
                """
                stdout, stderr = self.run_command(
                    f"nc -zv -w 5 {hostname} {port}", timeout=10)
                logger.info(f"Netcat check output: {stdout}\n {stderr}")
                return "open" in stderr

            def http_check():
                """
                Use curl to check if the specified hostname and port respond with an HTTP 200 status.

                Returns:
                    bool: True if the HTTP response code is 200, False otherwise.
                """
                stdout, stderr = self.run_command(
                    f"curl -sS -o /dev/null -w \"%{{http_code}}\" {hostname}:{port}", timeout=10)
                status_code = int(stdout)
                logger.info(f"HTTP check output: {stdout}\n {stderr}")
                return status_code == 200

            for attempt in range(MAX_RETRIES):
                if http_check() or nc_check():
                    logger.info(
                        f"Can connect to {hostname}:{port} on attempt {attempt + 1}.")
                    break
                else:
                    logger.warning(
                        f"Cannot connect to {hostname}:{port} (Attempt {attempt + 1}/{MAX_RETRIES}).")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                    else:
                        failed_hosts.append(target_host)

        if failed_hosts:
            logger.error(
                f"Failure to connect for the following hosts: {', '.join(failed_hosts)}")
            raise RuntimeError(
                "Failure to connect for one or more target hosts.")
        else:
            logger.info("All target hosts can be connected to.")

    def to_dict(self) -> dict:
        """
        Serializes the KaliEnvResource state to a dictionary.
        """
        return {
            'resource_id': self.resource_id,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S%z')
        }

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> 'KaliEnvResource':
        """
        Creates a KaliEnvResource instance from a serialized dictionary.
        """
        task_dir = os.path.dirname(os.path.dirname(data['bounty_dir']))
        bounty_number = os.path.basename(data['bounty_dir']).replace('bounty_', '')
        
        return cls(
            name=data['resource_id'],
            task_dir=task_dir,
            bounty_number=bounty_number,
            **kwargs
        )

    def save_to_file(self, filepath: str) -> None:
        """
        Saves the resource state to a JSON file.
        """
        import json
        state = self.to_dict()
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str, **kwargs) -> 'KaliEnvResource':
        """
        Loads a resource state from a JSON file.
        """
        import json
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data, **kwargs)