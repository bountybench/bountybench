import asyncio
from pathlib import Path

from prompts.prompts import DETECT_PATCH_PROMPT, TARGET_HOST_DETECT_PATCH_PROMPT
from utils.logger import get_main_logger
from workflows.patch_workflow import PatchWorkflow

logger = get_main_logger(__name__)


class DetectPatchWorkflow(PatchWorkflow):
    """Workflow for detecting vulnerabilities"""

    default_values = {
        "interactive": False,
        "use_helm": False,
        "use_mock_model": False,
        "max_input_tokens": 8192,
        "max_output_tokens": 4096,
        "vulnerability_type": "",  # No default vulnerability type
    }

    @property
    def use_agent_exploit(self):
        # Preserving current behavior - we may want to revisit this
        return True

    def _get_initial_prompt(self):
        """
        Provide the initial prompt for the workflow by reading the exploit report.

        Returns:
            str: The formatted initial prompt.
        """
        return (
            TARGET_HOST_DETECT_PATCH_PROMPT
            if self.repo_metadata["target_host"]
            else DETECT_PATCH_PROMPT
        )
