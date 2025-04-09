from dataclasses import dataclass
from pathlib import Path

from resources.base_resource import BaseResourceConfig
from resources.base_setup_resource import BaseSetupResource
from utils.logger import get_main_logger

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
        # Call the superclass constructor first
        super().__init__(resource_id, config)

        # Set required properties
        self.task_dir = self._resource_config.task_dir
        self.bounty_number = self._resource_config.bounty_number
        self.setup_script_name = "setup_bounty_env.sh"

        # Initialize bounty directory
        self.bounty_dir = self.task_dir / "bounties" / f"bounty_{self.bounty_number}"

        # Set work_dir for bounty setup
        self.work_dir = self.bounty_dir / "setup_files"

        # Run the setup process
        self.setup()

    def update_work_dir(self, new_work_dir: Path) -> None:
        """
        Update the work directory for this resource.
        Note:
            This will not restart the resource. Call restart() manually if needed.
        """
        if not new_work_dir.exists():
            raise FileNotFoundError(
                f"New work directory does not exist: {new_work_dir}"
            )

        logger.info(f"Updating work_dir from {self.work_dir} to {new_work_dir}")
        self.work_dir = new_work_dir

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

        # Override work_dir if it exists in the data
        if "work_dir" in data:
            instance.work_dir = Path(data["work_dir"])

        return instance
