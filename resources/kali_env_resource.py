import atexit
import os
import sys
import time
from typing import Dict, Optional, Tuple, Any
from resources.kali_env_resource_util import KaliEnvResourceUtil

import docker
from docker.models.containers import Container

from messages.action_messages.action_message import ActionMessage
from messages.action_messages.command_message import CommandMessage
from resources.base_resource import BaseResource
from resources.utils import get_stdout_text
from utils.logger import get_main_logger
from utils.progress_logger import start_progress, stop_progress
from dataclasses import dataclass
import os
from resources.base_resource import BaseResourceConfig
import signal
from contextlib import contextmanager

# Constants with type annotations
DOCKER_IMAGE: str = "cybench/bountyagent:latest"
ENTRYPOINT: str = "/usr/local/bin/dockerd-entrypoint.sh"

TIMEOUT_PER_COMMAND = 120
MAX_RETRIES = 3
RETRY_DELAY = 5

# Configure logging
logger = get_main_logger(__name__)

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
        self.util = KaliEnvResourceUtil()
        self.client = docker.from_env()
        self.container = self._start(self.resource_id, self._resource_config.volumes)
        self.util.validate_container_status(self.container, logger)
        self.target_host = self._resource_config.target_host
        self.socket = None # Socket for writing to the pseudo-terminal
        self._initialize_bounty_directory()
        
        if self.target_host:
            self.connect_to_target_hosts_check(self.target_host)

        atexit.register(self.stop)

    def _start(self, name: str, volumes: Optional[Dict[str, Dict[str, str]]]) -> Container:
        """
        Start a Kali Linux container to be used throughout the lifecycle.
        """
        for attempt in range(MAX_RETRIES):
            try:
                # Check for existing container and force remove it
                self._remove_existing_container(name)
                container = self._create_and_start_container(name, volumes,attempt)
                return container 

            except Exception as e:
                self.util.handle_start_error(e, attempt,logger)
    
    def stop(self):
        """Stop and remove the Docker container"""
        try: 
            if self.container:
                if self.container.status == 'running':
                    self.util.safe_execute(lambda:self.cleanup_tmp(), "tmp cleanup", logger)                   
                logger.info("Cleaning up: stopping and removing Docker container.")
    
                self.util.safe_execute(lambda: self.container.stop(timeout=1), "stopping container",logger)
                self.util.safe_execute(lambda: self.container.remove(force=True), "removing container",logger)
    
                self.container = None
                logger.info("Docker container cleaned up successfully.")
        except Exception as e:
            logger.error(f"Unexpected error during Docker container cleanup: {e}")

    def run(self, command_message: CommandMessage) -> ActionMessage:
        command_str = command_message.command
        stdout, stderr = self.run_command(command_str, TIMEOUT_PER_COMMAND)
        observation_text = stdout.strip() + stderr.strip()
        return ActionMessage(resource_id=self.resource_id, message=observation_text, prev=command_message)
    
    def run_command(self, command: str, timeout: int = 120, workdir: Optional[str] = None, tty: bool = False) -> Tuple[str, str]:
        command_str = command.lstrip().lstrip("*").lstrip()
        if len(command) > 33:
            command_str = command_str[:30] + "..."
        start_progress(f"Running command in Docker container (workdir: {workdir}): {command_str}")

        try:
            with timeout_context(timeout):
                if not tty:
                    return self._run_non_tty_command(command, workdir)
                else:
                    return self._run_tty_command(command, workdir)

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

    def _initialize_bounty_directory(self):
        if self._resource_config.task_dir and self._resource_config.bounty_number:
            self.bounty_dir = os.path.join(
                str(self._resource_config.task_dir),
                "bounties",
                f"bounty_{self._resource_config.bounty_number}"
            )
    
    def _remove_existing_container(self, name: str):
        try:
            print("-"*90)
            print(self.client.containers.get(name))
            print("in remove")
            print("-"*90)
            container = self.client.containers.get(name)
            logger.info(f"Container '{name}' already exists. Forcefully removing it.")
            start_progress(f"Removing existing container '{name}'...")
            self._force_remove_container(container, name)
        except docker.errors.NotFound:
            logger.info(f"No existing container named '{name}'.")
        finally:
            stop_progress()
    

    def _force_remove_container(self, container: Container, name: str):
        try:
            container.remove(force=True)
            self.util.verify_container_removal(name,logger)
        except docker.errors.APIError as e:
            logger.error(f"Force removal failed: {e}")
            raise
    
    def _create_and_start_container(self, name: str, volumes: Optional[Dict[str, Dict[str, str]]], attempt:int) -> Optional[Container]:
        start_progress(f"Starting a new Docker container (Attempt {attempt + 1}/{MAX_RETRIES})...")
        try:
            print(self.client.containers)
            print("in start")
            print("-"*90)
            container = self.client.containers.run(
                image=DOCKER_IMAGE,
                cgroupns="host",
                network="shared_net",
                volumes=volumes,
                entrypoint=ENTRYPOINT,
                detach=True,
                name=name
            )
            self.util.safe_execute(lambda: self.util.print_docker_log(container), "printing docker log")
            if not self.util.wait_for_container(container):
                self.util.handle_container_start_failure(container,logger)
            logger.info("Container started successfully.")
            return container
        finally:
            stop_progress()

    def cleanup_tmp(self):
        """Clean up temporary files"""
        try:
            logger.info("Cleaning up: removing tmp files.")
            cleanup_command = "rm -rf * .*"
            return self.run_command(cleanup_command, workdir="/app")
        except Exception as e:
            logger.error(f"Error cleaning up tmp files: {e}")

    def _run_non_tty_command(self, command: str, workdir: Optional[str]) -> Tuple[str, str]:
        exec_id = self.create_exec(command, workdir, tty=False)
        output = self.client.api.exec_start(exec_id, stream=False, demux=True)
        stdout, stderr = output or (None, None)
        stdout_text = get_stdout_text(stdout)
        stderr_text = get_stdout_text(stderr)
        logger.info(f"Command executed successfully in [line-mode].\nstdout: {stdout_text}\nstderr: {stderr_text}")
        return stdout_text, stderr_text

    def _run_tty_command(self, command: str, workdir: Optional[str]) -> Tuple[str, str]:
        if not self.socket:
            self._initialize_tty_socket(workdir)

        self.util.prepare_tty_command(self.socket, logger, command)
        output = self.util.read_tty_output(self.socket)
        stdout_text = self.util.process_tty_output(output, command)
        logger.info(f"Command executed successfully in [pty-mode].\nstdout: {stdout_text}\n")
        return stdout_text, ""

    def _initialize_tty_socket(self, workdir: Optional[str]):
        exec_id = self.create_exec("", workdir, tty=True)
        self.socket = self.client.api.exec_start(
            exec_id=exec_id, stream=True, demux=False, socket=True, tty=True
        )
        self.util.send_to_bash(self.socket,logger, 'export PS1="$"\n')
    
    def create_exec(self, command: str, workdir: Optional[str], tty: bool) -> str:
        exec_params = {
            "container": self.container.id,
            "cmd": ["/bin/bash", "-c", command] if not tty else ["/bin/bash"],
            "workdir": workdir,
            "stdin": tty,
            "stdout": True,
            "stderr": True,
            "tty": tty,
        }
        return self.client.api.exec_create(**exec_params)["Id"]

    def connect_to_target_hosts_check(self, target_hosts: str) -> None:
        """
        Checks if kali resource can connect on the specified target hosts with retries.

        Args:
            target_hosts (str): A string containing space-separated target hosts in the format hostname:port.
        """
        hosts = target_hosts.split()
        failed_hosts = []

        for target_host in hosts:
            hostname, port = self.util.parse_target_host(target_host,logger)

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