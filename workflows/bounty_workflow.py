from abc import ABC

from resources.utils import read_bounty_metadata, read_repo_metadata
from utils.logger import get_main_logger
from workflows.base_workflow import BaseWorkflow
from workflows.utils import setup_shared_network

logger = get_main_logger(__name__)


class BountyWorkflow(BaseWorkflow, ABC):
    def validate_arguments(self, kwargs):
        """
        Base validation for all bounty workflows
        """
        super().validate_arguments(kwargs)

        # All bounty workflows require task_dir and bounty_number
        required_base_args = ["task_dir", "bounty_number"]
        missing_args = [arg for arg in required_base_args if arg not in kwargs]
        if missing_args:
            raise ValueError(
                f"Missing required arguments for {self.name}: {', '.join(missing_args)}"
            )

    def _initialize(self):
        self.task_dir = self.params["task_dir"]
        self.bounty_number = self.params["bounty_number"]
        logger.info(
            f"Setting bounty parameters:\nTask dir: {self.task_dir}\nBounty number: {self.bounty_number}"
        )
        self.repo_metadata = read_repo_metadata(self.task_dir)
        self.bounty_metadata = read_bounty_metadata(self.task_dir, self.bounty_number)

        setup_shared_network()

    def _get_metadata(self):
        return {
            "repo_metadata": self.repo_metadata,
            "bounty_metadata": self.bounty_metadata,
        }

    def _get_task(self):
        return {"task_dir": self.task_dir, "bounty_number": self.bounty_number}
