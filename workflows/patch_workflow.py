import asyncio
from pathlib import Path

from phases.patch_phase import PatchPhase
from prompts.prompts import PATCH_PROMPT, STOP_TOKEN, TARGET_HOST_PATCH_PROMPT
from resources.utils import read_writeup
from utils.logger import get_main_logger
from workflows.bounty_workflow import BountyWorkflow

logger = get_main_logger(__name__)


class PatchWorkflow(BountyWorkflow):
    """Workflow for patching vulnerabilities"""

    required_args = ["task_dir", "bounty_number", "model", "phase_iterations"]
    optional_args = [
        "interactive",
        "use_helm",
        "use_mock_model",
        "max_input_tokens",
        "max_output_tokens",
    ]

    # Default values for optional arguments
    default_values = {
        "interactive": False,
        "use_helm": True,
        "use_mock_model": False,
        "max_input_tokens": 8192,
        "max_output_tokens": 4096,
    }

    @property
    def use_agent_exploit(self):
        # Preserving current behavior - we may want to revisit this
        return False

    def _create_phases(self):
        """Define and register phases specific to PatchWorkflow."""

        phase_kwargs = {
            "use_mock_model": self.params.get("use_mock_model"),
            "model": self.params.get("model"),
            "helm": self.params.get("use_helm"),
            "task_dir": self.task_dir,
            "bounty_number": self.bounty_number,
            "vulnerability_type": self.params.get("vulnerability_type"),
            "use_agent_exploit": self.use_agent_exploit,
            "task_description": read_writeup(self.task_dir, self.bounty_number),
            "stop_token": STOP_TOKEN,
            "target_host": self.repo_metadata["target_host"],
            "initial_prompt": self.initial_prompt,
            "info": self.repo_metadata.get("info", "")
            + "\n"
            + self.bounty_metadata.get("info", ""),
            "max_input_tokens": self.params.get("max_input_tokens"),
            "max_output_tokens": self.params.get("max_output_tokens"),
            "interactive": self.interactive,
            "max_iterations": self.params.get("phase_iterations"),
        }

        patch_phase = PatchPhase(workflow=self, **phase_kwargs)

        self._register_root_phase(patch_phase)

    def _get_initial_prompt(self) -> str:
        """
        Provide the initial prompt for the workflow by reading the exploit report.

        Returns:
            str: The formatted initial prompt.
        """
        return (
            TARGET_HOST_PATCH_PROMPT
            if self.repo_metadata["target_host"]
            else PATCH_PROMPT
        )
