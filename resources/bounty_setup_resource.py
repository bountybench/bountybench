from dataclasses import dataclass
from pathlib import Path

from resources.base_resource import BaseResourceConfig
from resources.base_setup_resource import BaseSetupResource
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

SETUP_FILES_DIR = "setup_files"


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
        # Call the superclass constructor first
        super().__init__(resource_id, config)

        # Set required properties
        self.task_dir = self._resource_config.task_dir
        self.bounty_number = self._resource_config.bounty_number
        self.setup_script_name = "setup_bounty_env.sh"

        # Initialize bounty directory
        self.bounty_dir = self.task_dir / "bounties" / f"bounty_{self.bounty_number}"

        # Set work_dir for bounty setup
        self.work_dir = self.bounty_dir / SETUP_FILES_DIR

        # Run the setup process
        self.setup()

    def update_work_dir(self, new_work_dir: Path) -> None:
        """
        Update the work directory for this resource, and stop existing resources
        This should be used if you want to run another bounty's setup_bounty_env.sh
        This does NOT run the bounty setup in the new directory
        """
        logger.debug(f"Stopping current bounty resource in {self.work_dir}")
        self.stop()
        if not new_work_dir.exists() or not new_work_dir.is_dir():
            raise FileNotFoundError(
                f"New work directory does not exist or is not a directory: {new_work_dir}"
            )

        if not new_work_dir.name == SETUP_FILES_DIR:
            raise ValueError(
                f"New work directory must end with {SETUP_FILES_DIR}: {new_work_dir}"
            )

        logger.debug(f"Updated work_dir from {self.work_dir} to {new_work_dir}")
        self.work_dir = new_work_dir

    def set_skip_setup(self, value: bool) -> None:
        logger.info(
            f"Current value of skip_setup: {self.skip_setup}. \n Setting skip_setup to {value}"
        )
        self.skip_setup = value

    def to_dict(self) -> dict:
        """
        Serializes the BountySetupResource state to a dictionary.
        """
        # Get the base dictionary from parent class
        base_dict = super().to_dict()

        # Add bounty-specific properties
        base_dict.update(
            {
                "bounty_dir": str(self.bounty_dir),
                "bounty_number": self.bounty_number,
            }
        )

        return base_dict

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> "BountySetupResource":
        """
        Creates a BountySetupResource instance from a serialized dictionary.
        """
        common_attrs = super().from_dict(data, **kwargs)

        config = BountySetupResourceConfig(
            task_dir=Path(data["task_dir"]),
            bounty_number=data["bounty_number"],
        )

        instance = cls(common_attrs["resource_id"], config)

        instance.container_names = common_attrs["container_names"]

        return instance
