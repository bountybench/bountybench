import atexit
import os
import sys
import time
import select
from typing import Dict, Optional, Tuple
import time


import docker
from docker.models.containers import Container

from messages.action_messages.action_message import ActionMessage
from messages.action_messages.command_message import CommandMessage
from resources.base_resource import BaseResource
from resources.utils import get_stdout_text
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

TIMEOUT_PER_COMMAND = 120
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
        print(f"KaliEnvResource started container {self.container.id} with status: {self.container.status}")


        # If the container isn't running, fail fast and print logs
        
        if self.container.status != "running":
            logs = self.container.logs().decode("utf-8")
            print(f"Container exited unexpectedly. Logs:\n{logs}")
            raise RuntimeError("Container exited unexpectedly after creation.")



        self.target_host = self._resource_config.target_host
        self.socket = None # Socket for writing to the pseudo-terminal
        
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


    


    def wait_for_container(self, container, timeout=10):
        """Waits for the container to enter 'running' state."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            container.reload()  # Refresh container status
            if container.status == "running":
                return True
            time.sleep(0.5)
        return False


    
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
                        #cgroupns="host",
                        network="shared_net",
                        volumes=volumes,
                        #entrypoint=ENTRYPOINT,
                        command="tail -f /dev/null",  # Keep container running
                        detach=True,
                        name=name,
                    )
                    logger.info("KaliEnvResource Docker container started successfully.")
                        # Inside `_start()`, right after container creation:
                    if not self.wait_for_container(container):
                        logs = container.logs().decode("utf-8")
                        print(f"Container failed to start. Logs:\n{logs}")
                        raise RuntimeError("Container failed to reach running state.")
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
        """Clean up temporary files"""
        try:
            logger.info("Cleaning up: removing tmp files.")
            cleanup_command = "rm -rf * .*"
            return self.run_command(cleanup_command, workdir="/app")
        except Exception as e:
            logger.error(f"Error cleaning up tmp files: {e}")

    def stop(self):
        """Stop and remove the Docker container"""
        try:
            if self.container:
                try:
                    self.cleanup_tmp()
                except Exception as e:
                    logger.error(f"Error during tmp cleanup: {e}")
                
                logger.info("Cleaning up: stopping and removing Docker container.")
                try:
                    self.container.stop(timeout=1)  # Short timeout for quicker shutdown
                except Exception as e:
                    logger.error(f"Error stopping container: {e}")
                
                try:
                    self.container.remove(force=True)  # Force remove in case stop failed
                except Exception as e:
                    logger.error(f"Error removing container: {e}")
                
                self.container = None
                logger.info("Docker container cleaned up successfully.")
        except Exception as e:
            logger.error(f"Error cleaning up Docker container: {e}")

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
        print(f"Running command inside container {self.container.id}. Status: {self.container.status}")


        if self.container.status != "running":
            logs = self.container.logs().decode("utf-8")
            print(f"Cannot exec into container, it's not running. Logs:\n{logs}")
            raise RuntimeError("Cannot execute command: container is not running.")


        try:
            if not tty:
                with timeout_context(timeout):
                    exec_id = self.client.api.exec_create(
                        container=self.container.id,
                        cmd=["/bin/bash", "-c", command],
                        workdir=workdir,
                        stdin=False,
                        stdout=True,
                        stderr=True,
                    )["Id"]

                    output = self.client.api.exec_start(exec_id, stream=False, demux=True)
                    stdout, stderr = output or (None, None)

                stdout_text = get_stdout_text(stdout)
                stderr_text = get_stdout_text(stderr)
                logger.info(f"Command executed successfully in [line-mode].\nstdout: {stdout_text}\nstderr: {stderr_text}")
                return stdout_text, stderr_text
            else:
                with timeout_context(timeout):
                    if not self.socket:
                        exec_id = self.client.api.exec_create(
                                container=self.container.id,
                                cmd=["/bin/bash"],
                                workdir=workdir,
                                stdin=True,
                                stdout=True,
                                stderr=True,
                                tty=True,
                            )["Id"]
                        
                        sock = self.client.api.exec_start(
                            exec_id=exec_id,
                            stream=True,
                            demux=False,   
                            socket=True,
                            tty=True,
                        )
                        self.socket = sock
                        self._send_to_bash('export PS1="$"\n')

                    self._clear_bash_output_buffer()
                    num_new_lines = self._count_trailing_new_lines(command)
                    command = command.strip()

                    if self._is_single_control_character(command):
                        command = command.strip().encode('utf-8').decode('unicode_escape')
                        self._send_to_bash(command)
                    else:
                        self._send_to_bash(command)
                        self._clear_bash_output_buffer()

                    for _ in range(num_new_lines):
                        self._send_to_bash('\n')

                    output = b''
                    sock_timeout = 30
                    end_time = time.time() + sock_timeout
                    last_data_time = time.time()    
                    max_inactivity = 3  # seconds
                    execution_time = time.time()

                    while execution_time < end_time:
                        rlist, _, _ = select.select([self.socket.fileno()], [], [], 1)
                        
                        if self.socket.fileno() in rlist:
                            chunk = self.socket._sock.recv(1024)
                            if not chunk:
                                break
                            output += chunk
                            last_data_time = time.time()
                        else:
                            break

                        if output and time.time() - last_data_time > max_inactivity:
                            # No data received for max_inactivity seconds
                            break

                        execution_time = time.time()
                    
                    if execution_time >= end_time and not output:
                        stdout_text = f"No output received for {sock_timeout} seconds."
                    else:
                        stdout_text = get_stdout_text(output)
                        stdout_text = self._clean_command_output(stdout_text, command)
                    logger.info(f"Command executed successfully in [pty-mode].\nstdout: {stdout_text}\n")
                    stderr_text = "" # Combined stdout and stderr in pty-mode
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
        
    def _send_to_bash(self, input_str: str):
        self.socket._sock.sendall(input_str.encode())  # why socket.write() does not work?
    
    def _count_trailing_new_lines(self, input_str: str) -> int:
        input_str = input_str.rstrip(' ')
        return len(input_str) - len(input_str.rstrip('\n'))

    def _is_single_control_character(self, s):
        s = s.strip()
        s = s.encode('utf-8').decode('unicode_escape')
        if len(s) != 1:
            return False
        return ord(s) < 32 or ord(s) == 127
    
    def _control_char_to_text(self, char: str) -> str:
        if ord(char) == 127:  # Special case for DEL
            return '^?'
        return f"^{chr(ord(char) + 64)}"
    

    def _clear_bash_output_buffer(self, timeout: float = 2.0):
        """
        Clears the bash output buffer by reading until no more data is available
        or until the timeout is reached.

        Copied from 
        """
        start_time = time.time()
        try:
            while time.time() - start_time < timeout:
                rlist, _, _ = select.select([self.socket.fileno()], [], [], 0.1)
                if self.socket.fileno() in rlist:
                    try:
                        chunk = self.socket._sock.recv(1024)
                    except OSError as e:
                        logger.error(f"Error while clearing bash buffer: {str(e)}")
                        break
                else:
                    # No data ready; buffer is clear
                    break
        except Exception as e:
            logger.error(f"Unexpected error while clearing bash buffer: {str(e)}")
        

    def _clean_command_output(self, raw_output: str, command_str: str) -> str:
        """
        Cleans the raw bash output to remove initialization strings and the echoed command.
        Also removes echoed multiline outputs for commands like `cat << EOF`.
        """
        import re

        # Use a regex to remove ANSI escape sequences
        cleaned_output = re.sub(r'\x1b\[[0-9;?]*[a-zA-Z]', '', raw_output)
        # Remove patterns like \r followed by digits, a comma, and more digits
        cleaned_output = re.sub(r'\r\d+,\s*\d*', '', cleaned_output)
        # Remove sequences like \r8, \r08, etc.
        cleaned_output = re.sub(r'\r\d*', '', cleaned_output)
        # Replace standalone carriage returns (\r) with nothing
        cleaned_output = cleaned_output.replace('\r', '')
        cleaned_output = cleaned_output.replace('\n\n$', '\n$')

        if self._is_single_control_character(command_str):
            command_str = self._control_char_to_text(command_str)

        # Escape command_str for regex safety
        command_pattern = re.escape(command_str.strip())

        # Use regex to find the command and split the output after the match
        match = re.search(f"^{command_pattern}.*$", cleaned_output, re.MULTILINE)
        # print("CLEANED_OUTPUT:", cleaned_output)
        # print("COMMAND PATTERN:", command_pattern)
        if not match:
            # print("No match found.")
            return cleaned_output.strip()  # If no match, return the original stripped output

        # Get everything after the command match
        start_index = match.end()
        cleaned_output = cleaned_output[start_index:].strip()

        return cleaned_output

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