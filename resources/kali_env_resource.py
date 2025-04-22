import atexit
import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import docker
from docker.models.containers import Container

from messages.action_messages.action_message import ActionMessage
from messages.action_messages.command_message import CommandMessage
from resources.base_resource import BaseResourceConfig
from resources.kali_env_resource_util import KaliEnvResourceUtil
from resources.runnable_base_resource import RunnableBaseResource
from resources.utils import get_stdout_text
from utils.git_utils import git_commit
from utils.logger import get_main_logger
from utils.progress_logger import start_progress, stop_progress

# Constants with type annotations
DOCKER_IMAGE: str = "cybench/bountyagent:latest"
ENTRYPOINT: str = "/usr/local/bin/entrypoint.sh"
DOCKER_CLIENT_INIT_TIMEOUT: int = 300

TIMEOUT_PER_COMMAND: int = 600
MAX_RETRIES: int = 3
RETRY_DELAY: int = 5

# Use a 20-minute timeout for pip installation
PIP_INSTALL_TIMEOUT: int = 1200

# Constants for ANSI color codes for printing
YELLOW = "\033[93m"
RESET = "\033[0m"

# Configure logging
logger = get_main_logger(__name__)

import threading
from contextlib import contextmanager


@contextmanager
def timeout_context(seconds):
    """Thread-safe timeout context manager."""

    def check_timeout():
        if not timeout_occurred[0]:
            timeout_occurred[0] = True

    timeout_occurred = [False]
    timer = threading.Timer(seconds, check_timeout)
    timer.daemon = True

    try:
        timer.start()
        yield
        if timeout_occurred[0]:
            raise TimeoutError("Timed out!")
    finally:
        timer.cancel()


@dataclass
class KaliEnvResourceConfig(BaseResourceConfig):
    """Configuration for KaliEnvResource"""

    task_dir: Optional[Path] = None
    bounty_number: Optional[str] = None
    volumes: Optional[Dict[str, Dict[str, str]]] = None
    target_hosts: Optional[List[str]] = None
    install_command: Optional[str] = None
    is_python: Optional[bool] = None
    disable_cleanup: Optional[bool] = None

    def validate(self) -> None:
        """Validate KaliEnv configuration"""
        if self.task_dir and not self.task_dir.exists():
            raise ValueError(f"Invalid task_dir: {self.task_dir}")
        if self.volumes:
            for host_path in self.volumes.keys():
                parent_dir = os.path.dirname(host_path)
                if not os.path.exists(parent_dir):
                    raise ValueError(
                        f"Invalid volume host path parent directory: {parent_dir}"
                    )


class KaliEnvResource(RunnableBaseResource):
    """Kali Linux Environment Resource"""

    def __init__(self, resource_id: str, config: KaliEnvResourceConfig):
        super().__init__(resource_id, config)
        self.util = KaliEnvResourceUtil()
        self.client = docker.from_env(timeout=DOCKER_CLIENT_INIT_TIMEOUT)
        self.container = self._start(self.resource_id, self._resource_config.volumes)
        self.util.validate_container_status(self.container, logger)
        self.target_hosts = self._resource_config.target_hosts
        self.install_command = self._resource_config.install_command
        self.is_python = self._resource_config.is_python
        self.disable_cleanup = self._resource_config.disable_cleanup
        self.socket = None  # Socket for writing to the pseudo-terminal
        self._initialize_bounty_directory()

        if self.target_hosts:
            self.connect_to_target_hosts_check(self.target_hosts)

        atexit.register(self.stop)

    def _start(
        self, name: str, volumes: Optional[Dict[str, Dict[str, str]]]
    ) -> Container:
        """
        Start a Kali Linux container to be used throughout the lifecycle.
        """
        for attempt in range(MAX_RETRIES):
            try:
                # Check for existing container and force remove it
                self._remove_existing_container(name)
                container = self._create_and_start_container(name, volumes, attempt)
                return container

            except Exception as e:
                self.util.handle_start_error(e, attempt, logger)

    def stop(self):
        """Stop and remove the Docker container"""
        try:
            if self.container:
                if self.container.status == "running":
                    self.util.safe_execute(
                        lambda: self.cleanup_tmp(), "tmp cleanup", logger
                    )
                logger.debug("Cleaning up: stopping and removing Docker container.")

                self.util.safe_execute(
                    lambda: self.container.stop(timeout=1), "stopping container", logger
                )
                self.util.safe_execute(
                    lambda: self.container.remove(force=True),
                    "removing container",
                    logger,
                )

                self.container = None
                logger.debug("Docker container cleaned up successfully.")
        except Exception as e:
            logger.error(f"Unexpected error during Docker container cleanup: {e}")

    def run(self, command_message: CommandMessage) -> ActionMessage:
        command_str = command_message.command
        stdout, stderr = self.run_command(command_str, TIMEOUT_PER_COMMAND)
        observation_text = stdout.rstrip() + stderr.strip()
        return ActionMessage(
            resource_id=self.resource_id, message=observation_text, prev=command_message
        )

    def run_command(
        self,
        command: str,
        timeout: int = 120,
        workdir: Optional[str] = None,
        tty: bool = False,
        verbose: bool = True,
    ) -> Tuple[str, str]:
        command_str = command.lstrip().lstrip("*").lstrip()
        if len(command) > 33:
            command_str = command_str[:30] + "..."
        logger.info(
            f"Running command in Docker container (workdir: {workdir}): {command_str}"
        )

        try:
            with timeout_context(timeout):
                if not tty:
                    return self._run_non_tty_command(command, timeout, workdir, verbose)
                else:
                    return self._run_tty_command(command, workdir, verbose)

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
        # Initialize bounty directory if task_dir and bounty_number provided
        if self._resource_config.task_dir and self._resource_config.bounty_number:
            self.bounty_dir = (
                self._resource_config.task_dir
                / "bounties"
                / f"bounty_{self._resource_config.bounty_number}"
            )
            self._install_repo_in_editable_mode()

    def _install_repo_in_editable_mode(self):
        """
        Detects the repository type and installs it in editable mode.
        Only installs Python repositories, skips Node.js repositories.
        """
        if not self._resource_config.task_dir:
            logger.warning(
                "Cannot install repo in editable mode: task_dir not provided"
            )
            return

        codebase_path = "/app/codebase"
        cmd = f"[ -d {codebase_path} ] && echo 'exists' || echo 'not_exists'"
        stdout, _ = self.run_command(cmd, TIMEOUT_PER_COMMAND)
        if stdout.strip() == "not_exists":
            logger.warning(
                f"Directory {codebase_path} does not exist in the container. Skipping installation"
            )
            return

        # Check if repository is Python
        is_python = self._is_python_repo(codebase_path)

        if is_python:
            logger.debug(
                f"Detected Python repository at {codebase_path}. Installing in editable mode..."
            )
            # Use the custom install command if provided, otherwise default to editable install
            cmd = (
                self.install_command
                if self.install_command is not None
                else "pip install -e ."
            )
            # Omit printing
            stdout, stderr = self.run_command(
                command=cmd,
                timeout=PIP_INSTALL_TIMEOUT,
                workdir=codebase_path,
                verbose=False,
            )
            # logger.debug(f"Python repo installation result: {stdout}\n{stderr}")

            host_path = self._map_container_path_to_host(codebase_path)
            if host_path:
                logger.debug(
                    f"Updating git history to include changes from installation in latest commit"
                )
                git_commit(host_path)
            else:
                logger.warning(
                    f"Could not determine host path for {codebase_path}. Skipping git commit."
                )
            return

        # Check if Node.js repo - just log but don't install
        elif self._is_node_repo(codebase_path):
            logger.debug(
                f"Detected Node.js repository at {codebase_path}. Skipping installation."
            )
            return

        logger.debug(
            "No recognized Python repository found in any codebase location. Skipping installation."
        )

    def _map_container_path_to_host(self, container_path: str) -> Optional[str]:
        """
        Maps a path in the container to its corresponding path on the host system.
        This is needed for Git operations which must be performed on the host.
        """
        if not self._resource_config.volumes:
            return None

        # Standardize container path for comparison
        container_path = os.path.normpath(container_path)

        # Check each volume mapping to see if the container path is within it
        for host_path, mount_config in self._resource_config.volumes.items():
            container_mount = mount_config.get("bind", "")
            if container_path.startswith(container_mount):
                # Replace the container mount point with the host path
                relative_path = os.path.relpath(container_path, container_mount)
                mapped_host_path = os.path.join(host_path, relative_path)
                return os.path.normpath(mapped_host_path)

        # If we get here, no matching volume was found
        return None

    def _is_python_repo(self, codebase_path):
        """Check if the repository is a Python repository by looking for setup.py or pyproject.toml"""
        if self.is_python is not None:
            return self.is_python
        cmd = f"ls {codebase_path}/setup.py {codebase_path}/pyproject.toml 2>/dev/null || true"
        stdout, _ = self.run_command(cmd, TIMEOUT_PER_COMMAND)
        return "setup.py" in stdout or "pyproject.toml" in stdout

    def _is_node_repo(self, codebase_path):
        """Check if the repository is a Node.js repository by looking for package.json"""
        cmd = f"ls {codebase_path}/package.json 2>/dev/null || true"
        stdout, _ = self.run_command(cmd, TIMEOUT_PER_COMMAND)
        return "package.json" in stdout

    def _remove_existing_container(self, name: str):
        try:
            print("-" * 90)
            print(self.client.containers.get(name))
            print("in remove")
            print("-" * 90)
            container = self.client.containers.get(name)
            logger.debug(f"Container '{name}' already exists. Forcefully removing it.")
            start_progress(f"Removing existing container '{name}'...")
            self._force_remove_container(container, name)
        except docker.errors.NotFound:
            logger.debug(f"No existing container named '{name}'.")
        finally:
            stop_progress()

    def _force_remove_container(self, container: Container, name: str):
        try:
            container.remove(force=True)
            self.util.verify_container_removal(name, logger)
        except docker.errors.APIError as e:
            logger.error(f"Force removal failed: {e}")
            raise

    def _create_and_start_container(
        self, name: str, volumes: Optional[Dict[str, Dict[str, str]]], attempt: int
    ) -> Optional[Container]:
        start_progress(
            f"Starting a new Docker container (Attempt {attempt + 1}/{MAX_RETRIES})..."
        )
        try:
            # Pull the latest image before starting the container
            logger.debug(f"Pulling the latest Docker image: {DOCKER_IMAGE}")
            try:
                self.client.images.pull(DOCKER_IMAGE)
                logger.debug(f"Successfully pulled the latest image: {DOCKER_IMAGE}")
            except Exception as e:
                logger.warning(
                    f"Failed to pull the latest image: {e}. Will use existing image if available."
                )

            print(self.client.containers)
            print("in start")
            print("-" * 90)
            container = self.client.containers.run(
                image=DOCKER_IMAGE,
                cgroupns="host",
                network="shared_net",
                volumes=volumes,
                entrypoint=ENTRYPOINT,
                privileged=True,
                detach=True,
                name=name,
                command=["tail", "-f", "/dev/null"],
            )
            self.util.safe_execute(
                lambda: self.util.print_docker_log(container), "printing docker log"
            )
            if not self.util.wait_for_container(container):
                self.util.handle_container_start_failure(container, logger)
            logger.debug("Container started successfully.")
            return container
        finally:
            stop_progress()

    def cleanup_tmp(self):
        """Clean up temporary files"""
        if self.disable_cleanup:
            return
        try:
            logger.debug("Cleaning up: removing tmp files.")
            cleanup_command = "rm -rf * .*"
            return self.run_command(cleanup_command, workdir="/app")
        except Exception as e:
            logger.error(f"Error cleaning up tmp files: {e}")

    def _run_non_tty_command(
        self,
        command: str,
        timeout: int,
        workdir: Optional[str] = None,
        verbose: bool = True,
    ) -> Tuple[str, str]:
        exec_id = self.create_exec(command, workdir, tty=False)
        output_stream = self.client.api.exec_start(exec_id, stream=True, demux=True)

        stdout_chunks = []
        stderr_chunks = []
        stop_event = threading.Event()

        def stream_output():
            try:
                for stdout, stderr in output_stream:
                    if stop_event.is_set():
                        break
                    if stdout:
                        text = get_stdout_text(stdout)
                        if verbose:
                            print(text, end="")
                        stdout_chunks.append(text)
                    if stderr:
                        text = get_stdout_text(stderr)
                        if verbose:
                            print(f"{YELLOW}{text}{RESET}", end="", file=sys.stderr)
                        stderr_chunks.append(text)
            except Exception as e:
                logger.warning(f"Exec stream closed: {e}")

        stream_thread = threading.Thread(target=stream_output, daemon=True)
        stream_thread.start()

        exec_inspect = self.client.api.exec_inspect
        start_time = time.time()

        while True:
            exec_info = exec_inspect(exec_id)
            if not exec_info["Running"]:
                break
            if time.time() - start_time > timeout:
                stop_event.set()
                logger.warning(f"Exec command timed out after {timeout} seconds")
                return "", f"Timeout after {timeout} seconds"
            time.sleep(2)

        stop_event.set()
        stream_thread.join(timeout=5)

        stdout_text = "".join(stdout_chunks)
        stderr_text = "".join(stderr_chunks)

        logger.info(f"Command executed successfully in [line-mode].")
        return stdout_text, stderr_text

    def _run_tty_command(
        self, command: str, workdir: Optional[str], verbose: bool = True
    ) -> Tuple[str, str]:
        if not self.socket:
            self._initialize_tty_socket(workdir)

        self.util.prepare_tty_command(self.socket, logger, command)
        output = self.util.read_tty_output(self.socket)
        stdout_text = self.util.process_tty_output(output, command)
        logger.info(f"Command executed successfully in [pty-mode].\n")
        if verbose:
            logger.info(f"stdout: {stdout_text}\n")
        return stdout_text, ""

    def _initialize_tty_socket(self, workdir: Optional[str]):
        exec_id = self.create_exec("", workdir, tty=True)
        self.socket = self.client.api.exec_start(
            exec_id=exec_id, stream=True, demux=False, socket=True, tty=True
        )
        self.util.send_to_bash(self.socket, logger, 'export PS1="$"\n')

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

    def connect_to_target_hosts_check(self, target_hosts: List[str]) -> None:
        """
        Checks if kali resource can connect on the specified target hosts with retries.

        Args:
            target_hosts (str): A List[str] where each element contains space-separated target hosts in the format hostname:port.
        """
        all_hosts = []
        # Note repo metadata.json uses str of space-separated hosts, bounty_metadata.json uses a list
        # TODO: Make target host metadata format consistent

        for target_host in target_hosts:
            all_hosts += target_host.split()

        failed_hosts = []

        for target_host in all_hosts:
            hostname, port = self.util.parse_target_host(target_host, logger)

            print(f"Checking out {hostname} with {port}")

            def nc_check():
                """
                Use netcat to check if the specified hostname and port are open.

                Returns:
                    bool: True if the port is open, False otherwise.
                """
                stdout, stderr = self.run_command(
                    f"nc -zv -w 5 {hostname} {port}", timeout=10
                )
                logger.debug(f"Netcat check output: {stdout}\n {stderr}")
                # Check both stdout and stderr for "open" as different nc versions output to different streams
                return "open" in stdout or "open" in stderr

            def http_check():
                """
                Use curl to check if the specified hostname and port respond with an HTTP status.

                Returns:
                    bool: True if the HTTP response indicates the server is operational.
                """
                stdout, stderr = self.run_command(
                    f'curl -sS -o /dev/null -w "%{{http_code}}" {hostname}:{port}',
                    timeout=10,
                )
                logger.debug(f"HTTP check output: {stdout}\n {stderr}")

                try:
                    status_code = int(stdout.strip())
                    # 2xx success, 3xx redirect, 4xx client error all indicate server is operational
                    # Only 5xx server errors indicate potential server issues
                    return 200 <= status_code < 500
                except (ValueError, TypeError):
                    logger.warning(
                        f"Failed to parse HTTP status code from output: '{stdout}'"
                    )
                    return False

            for attempt in range(MAX_RETRIES):
                if http_check() or nc_check():
                    logger.debug(
                        f"Can connect to {hostname}:{port} on attempt {attempt + 1}."
                    )
                    break
                else:
                    logger.warning(
                        f"Cannot connect to {hostname}:{port} (Attempt {attempt + 1}/{MAX_RETRIES})."
                    )
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                    else:
                        failed_hosts.append(target_host)

        if failed_hosts:
            logger.error(
                f"Failure to connect for the following hosts: {', '.join(failed_hosts)}"
            )
            raise RuntimeError("Failure to connect for one or more target hosts.")
        else:
            logger.debug("All target hosts can be connected to.")

    def to_dict(self) -> dict:
        """
        Serializes the KaliEnvResource state to a dictionary.
        """
        return {
            "resource_id": self.resource_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> "KaliEnvResource":
        """
        Creates a KaliEnvResource instance from a serialized dictionary.
        """
        task_dir = (
            Path(data["bounty_dir"]).parent.parent if data["bounty_dir"] else None
        )
        bounty_number = (
            Path(data["bounty_dir"]).name.replace("bounty_", "")
            if data["bounty_dir"]
            else None
        )

        return cls(
            name=data["resource_id"],
            task_dir=task_dir,
            bounty_number=bounty_number,
            **kwargs,
        )

    def save_to_file(self, filepath: str) -> None:
        """
        Saves the resource state to a JSON file.
        """
        import json

        state = self.to_dict()
        with open(filepath, "w") as f:
            json.dump(state, f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str, **kwargs) -> "KaliEnvResource":
        """
        Loads a resource state from a JSON file.
        """
        import json

        with open(filepath, "r") as f:
            data = json.load(f)
        return cls.from_dict(data, **kwargs)
