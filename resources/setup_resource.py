import atexit
import re
import time
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from typing import List, Optional

from resources.base_resource import BaseResource, BaseResourceConfig
from resources.utils import run_command
from utils.logger import get_main_logger
from utils.progress_logger import start_progress, stop_progress

logger = get_main_logger(__name__)


@dataclass
class SetupResourceConfig(BaseResourceConfig):
    """Configuration for SetupResource"""

    bounty_level_setup: bool
    task_dir: Path
    bounty_number: Optional[str] = None

    def validate(self) -> None:
        """Validate Setup configuration"""
        if not self.task_dir.exists():
            raise ValueError(f"Invalid task_dir: {self.task_dir}")


class SetupResource(BaseResource):
    """SetupResource for initializing and managing containers."""

    def __init__(self, resource_id: str, config: SetupResourceConfig):
        # Call the superclass constructor first
        super().__init__(resource_id, config)

        self.task_dir = self._resource_config.task_dir

        # Access the configuration
        self.bounty_level_setup = self._resource_config.bounty_level_setup
        self.role = "bounty_resource" if self.bounty_level_setup else "repo_resource"

        if self.bounty_level_setup:
            if not self._resource_config.bounty_number:
                raise ValueError("Bounty number is required for bounty_resource setup.")
            self.bounty_dir = (
                self.task_dir
                / "bounties"
                / f"bounty_{self._resource_config.bounty_number}"
            )
        else:
            self.bounty_dir = None

        # Initialize container management
        self.container_names: List[str] = []
        self.health_check_timeout = 120

        try:
            self._start()
        except Exception as e:
            logger.error(f"Failed to initialize setup resource '{resource_id}': {e}")
            self.stop()  # Ensure we clean up resources in case of failure
            raise

        atexit.register(self.stop)

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

    def _start(self) -> None:
        """Start the environment by running the appropriate setup script."""
        setup_script = (
            "setup_bounty_env.sh" if self.bounty_level_setup else "setup_repo_env.sh"
        )
        work_dir = (
            self.bounty_dir / "setup_files"
            if self.bounty_level_setup
            else self.task_dir
        )

        if not work_dir.exists():
            raise FileNotFoundError(f"Work directory does not exist: {work_dir}")

        try:
            start_progress(f"Executing {setup_script} in {work_dir}")
            result = None  # Initialize result variable

            try:
                # Fix and prepare the script
                script_path = work_dir / setup_script
                if not script_path.exists():
                    raise FileNotFoundError(f"Setup script not found: {script_path}")

                # Fix script format and make executable
                self.fix_script_format(script_path)

                # On macOS, try running with bash explicitly if direct execution fails
                try:
                    result = run_command(
                        command=[f"./{setup_script}"], work_dir=str(work_dir)
                    )
                except OSError as e:
                    if e.errno == 8:  # Exec format error
                        logger.warning(
                            f"Direct execution failed, trying with explicit bash for {setup_script}"
                        )
                        result = run_command(
                            command=["bash", f"./{setup_script}"],
                            work_dir=str(work_dir),
                        )
                    else:
                        raise  # Re-raise if it's not an exec format error

                if result.returncode != 0:
                    raise RuntimeError(
                        f"Setup script failed with return code {result.returncode}"
                    )

            except Exception as e:
                logger.error(
                    f"Unable to successfully execute {setup_script} at {self.resource_id}: {e}"
                )
                raise RuntimeError(
                    f"Unable to successfully execute {setup_script} at {self.resource_id}: {e}"
                )
            finally:
                stop_progress()

            if (
                result and result.stdout
            ):  # Only process output if result exists and has stdout
                logger.info(f"Environment setup complete for {self.resource_id}")
                self.container_names = self.extract_container_names(
                    result.stdout, result.stderr
                )

                if self.container_names:
                    try:
                        success = self.wait_until_all_containers_healthy()
                        if not success:
                            raise RuntimeError(
                                f"Wait until all containers healthy returned {success}"
                            )
                    except Exception as e:
                        raise RuntimeError(
                            f"Failed to wait until all containers healthy: {e}"
                        )
            else:
                raise RuntimeError(f"No output from setup script {setup_script}")

        except FileNotFoundError as e:
            logger.error(str(e))
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
        work_dir = (
            self.bounty_dir / "setup_files"
            if self.bounty_level_setup
            else self.task_dir
        )
        docker_compose_file = work_dir / "docker-compose.yml"

        if docker_compose_file.exists():
            logger.info(f"Stopping docker in {work_dir}")
            try:
                run_command(
                    command=["docker", "compose", "down", "-v"], work_dir=str(work_dir)
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

    def to_dict(self) -> dict:
        """
        Serializes the SetupResource state to a dictionary.
        """
        return {
            "bounty_level_setup": self.bounty_level_setup,
            "task_dir": str(self.task_dir),
            "bounty_dir": str(self.bounty_dir) if self.bounty_dir else None,
            "resource_id": self.resource_id,
            "role": self.role,
            "container_names": self.container_names,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> "SetupResource":
        """
        Creates a SetupResource instance from a serialized dictionary.
        """
        bounty_number = (
            Path(data["bounty_dir"]).name.replace("bounty_", "")
            if data["bounty_dir"]
            else None
        )

        config = SetupResourceConfig(
            bounty_level_setup=data["bounty_level_setup"],
            task_dir=Path(data["task_dir"]),
            bounty_number=bounty_number,
        )
        instance = cls(data["resource_id"], config)
        instance.container_names = data["container_names"]
        return instance

    def save_to_file(self, filepath: Path) -> None:
        """
        Saves the resource state to a JSON file.
        """
        import json

        state = self.to_dict()
        filepath.write_text(json.dumps(state, indent=2))

    @classmethod
    def load_from_file(cls, filepath: Path, **kwargs) -> "SetupResource":
        """
        Loads a resource state from a JSON file.
        """
        import json

        data = json.loads(filepath.read_text())
        return cls.from_dict(data, **kwargs)
