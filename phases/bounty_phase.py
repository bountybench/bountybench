import os
import subprocess
from abc import ABC
from typing import List, Type

from agents.base_agent import BaseAgent
from phases.base_phase import BasePhase
from prompts.vulnerability_prompts import get_specialized_instructions
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


class BountyPhase(BasePhase, ABC):
    AGENT_CLASSES: List[Type[BaseAgent]] = []

    def _create_initial_agent_message(self) -> None:
        """Create the initial agent message for the bounty phase."""
        if self.params.get("task_dir"):
            codebase_structure = subprocess.run(
                ["tree", "-L", "4"],
                cwd=os.path.join(self.params.get("task_dir"), "tmp"),
                capture_output=True,
                text=True,
            ).stdout
            self.params["codebase"] = "$ tree -L 4\n" + codebase_structure

        self.params["specialized_instructions"] = (
            get_specialized_instructions(self.params.get("vulnerability_type"))
            if self.params.get("vulnerability_type")
            else ""
        )

        if self.params.get("vulnerability_type"):
            self.params["vulnerability_type"] += " "

        super()._create_initial_agent_message()
