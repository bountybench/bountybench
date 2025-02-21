from abc import ABC

from resources.utils import read_bounty_metadata, read_repo_metadata
from workflows.base_workflow import BaseWorkflow
from workflows.utils import setup_shared_network


class BountyWorkflow(BaseWorkflow, ABC):
    def _initialize(self):
        self.task_dir = self.params["task_dir"]
        self.bounty_number = self.params["bounty_number"]
        self.repo_metadata = read_repo_metadata(str(self.task_dir))
        self.bounty_metadata = read_bounty_metadata(
            str(self.task_dir), self.bounty_number
        )

        setup_shared_network()

    def _get_metadata(self):
        return {
            "repo_metadata": self.repo_metadata,
            "bounty_metadata": self.bounty_metadata,
        }

    def _get_task(self):
        return {"task_dir": self.task_dir, "bounty_number": self.bounty_number}
