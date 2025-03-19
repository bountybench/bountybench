import os
import subprocess
from abc import ABC
from pathlib import Path
from typing import Any, List, Type

from agents.base_agent import BaseAgent
from phases.base_phase import BasePhase
from prompts.vulnerability_prompts import get_specialized_instructions
from utils.logger import get_main_logger
from workflows.base_workflow import BaseWorkflow

logger = get_main_logger(__name__)


class BountyPhase(BasePhase, ABC):
    AGENT_CLASSES: List[Type[BaseAgent]] = []

    def __init__(self, workflow: "BaseWorkflow", **kwargs):
        """
        Initialize the PatchPhase.

        Args:
            workflow (BaseWorkflow): The parent workflow.
            **kwargs: Additional keyword arguments.
        """
        self.model: str = kwargs.get("model", "")
        self.helm: Any = kwargs.get("helm")
        self.bounty_number: str = kwargs.get("bounty_number", "")
        self.use_mock_model: str = kwargs.get("use_mock_model")

        self._initial_prompt: str = kwargs.get("initial_prompt", "")
        self.bounty_dir: Path = (
            workflow.task_dir / "bounties" / f"bounty_{self.bounty_number}"
        )

        self.tmp_dir: Path = (
            workflow.task_dir
            / "bounties"
            / f"bounty_{self.bounty_number}"
            / f"tmp_{workflow.workflow_message.workflow_id}"
        )

        super().__init__(workflow, **kwargs)

    def _create_initial_agent_message(self) -> None:
        """Create the initial agent message for the bounty phase."""
        if self.params.get("task_dir"):
            codebase_structure = subprocess.run(
                ["tree", "-L", "4"],
                cwd=str(self.tmp_dir),
                capture_output=True,
                text=True,
            ).stdout

            lines = codebase_structure.splitlines()
            all_words = codebase_structure.split()
            total_allowed_words = 200

            if len(all_words) > total_allowed_words:
                # Build top part (first ~100 words)
                top_part = []
                word_count = 0
                for line in lines:
                    line_word_len = len(line.split())
                    if word_count + line_word_len <= 100:
                        top_part.append(line)
                        word_count += line_word_len
                    else:
                        remaining = 100 - word_count
                        if remaining > 0:
                            partial_line = " ".join(line.split()[:remaining])
                            top_part.append(partial_line)
                        break

                # Build bottom part (last ~100 words)
                bottom_part = []
                word_count = 0
                for line in reversed(lines):
                    line_word_len = len(line.split())
                    if word_count + line_word_len <= 100:
                        bottom_part.insert(0, line)
                        word_count += line_word_len
                    else:
                        remaining = 100 - word_count
                        if remaining > 0:
                            partial_line = " ".join(line.split()[-remaining:])
                            bottom_part.insert(0, partial_line)
                        break

                trimmed_structure = "\n".join(top_part + ["    ..."] + bottom_part)
            else:
                trimmed_structure = codebase_structure

            self.params["codebase"] = "$ tree -L 4\n" + trimmed_structure

        self.params["specialized_instructions"] = (
            get_specialized_instructions(self.params.get("vulnerability_type"))
            if self.params.get("vulnerability_type")
            else ""
        )

        if self.params.get("vulnerability_type"):
            self.params["vulnerability_type"] += " "

        super()._create_initial_agent_message()
