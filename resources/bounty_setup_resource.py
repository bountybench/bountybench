import atexit
import re
import time
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from typing import List, Optional

from resources.base_resource import BaseResourceConfig
from resources.utils import run_command
from resources.base_setup_resource import BaseSetupResource
from utils.logger import get_main_logger
from utils.progress_logger import start_progress, stop_progress

logger = get_main_logger(__name__)


@dataclass
class BountySetupResourceConfig(BaseResourceConfig):
    """Configuration for BountySetupResource"""

    task_dir: Path
    bounty_number: str

    def validate(self) -> None:
        """Validate Bounty Setup configuration"""
        if not self.task_dir.exists():
            raise ValueError(f"Invalid task_dir: {self.task_dir}")
        if not self.bounty_number:
            raise ValueError("Bounty number is required for bounty setup.")


class BountySetupResource(BaseSetupResource):
    """BountySetupResource for initializing and managing bounty-level containers."""

    def __init__(self, resource_id: str, config: BountySetupResourceConfig):
        # Call the superclass constructor
        super().__init__(resource_id, config)

        self.task_dir = self._resource_config.task_dir
        self.bounty_number = self._resource_config.bounty_number
        self.role = "bounty_resource"
        
        # Initialize bounty directory
        self.bounty_dir = (
            self.task_dir
            / "bounties"
            / f"bounty_{self.bounty_number}"
        )
        
        # Set work_dir for bounty setup
        self.work_dir = self.bounty_dir / "setup_files"

        try:
            self._start()
        except Exception as e:
            logger.error(f"Failed to initialize bounty setup resource '{resource_id}': {e}")
            self.stop()  # Ensure we clean up resources in case of failure
            raise

        atexit.register(self.stop)

    def _start(self) -> None:
        """Start the bounty environment by running the bounty setup script."""
        setup_script = "setup_bounty_env.sh"

        if not self.work_dir.exists():
            raise FileNotFoundError(f"Work directory does not exist: {self.work_dir}")

        try:
            start_progress(f"Executing {setup_script} in {self.work_dir}")
            result = None  # Initialize result variable

            try:
                # Fix and prepare the script
                script_path = self.work_dir / setup_script
                if not script_path.exists():
                    raise FileNotFoundError(f"Setup script not found: {script_path}")

                # Fix script format and make executable
                self.fix_script_format(script_path)

                # On macOS, try running with bash explicitly if direct execution fails
                try:
                    result = run_command(
                        command=[f"./{setup_script}"], work_dir=str(self.work_dir)
                    )
                except OSError as e:
                    if e.errno == 8:  # Exec format error
                        logger.warning(
                            f"Direct execution failed, trying with explicit bash for {setup_script}"
                        )
                        result = run_command(
                            command=["bash", f"./{setup_script}"],
                            work_dir=str(self.work_dir),
                        )
                    else:
                        raise  # Re-raise if it's not an exec format error

                if result.returncode != 0:
                    raise RuntimeError(
                        f"Bounty setup script failed with return code {result.returncode}"
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
                logger.info(f"Bounty environment setup complete for {self.resource_id}")
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
                raise RuntimeError(f"No output from bounty setup script {setup_script}")

        except FileNotFoundError as e:
            logger.error(str(e))
            raise
        except Exception as e:
            logger.error(f"Unable to set up bounty environment at {self.resource_id}: {e}")
            raise

    def to_dict(self) -> dict:
        """
        Serializes the BountySetupResource state to a dictionary.
        """
        return {
            "task_dir": str(self.task_dir),
            "bounty_dir": str(self.bounty_dir),
            "resource_id": self.resource_id,
            "role": self.role,
            "bounty_number": self.bounty_number,
            "container_names": self.container_names,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> "BountySetupResource":
        """
        Creates a BountySetupResource instance from a serialized dictionary.
        """
        config = BountySetupResourceConfig(
            task_dir=Path(data["task_dir"]),
            bounty_number=data["bounty_number"],
        )
        instance = cls(data["resource_id"], config)
        instance.container_names = data["container_names"]
        return instance