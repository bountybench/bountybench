import asyncio
from pathlib import Path

from phases.detect_patch_phase import DetectPatchPhase
from prompts.prompts import STOP_TOKEN, build_prompt
from resources.utils import extract_bounty_title, read_writeup
from utils.logger import get_main_logger
from workflows.bounty_workflow import BountyWorkflow

logger = get_main_logger(__name__)


class DetectPatchWorkflow(BountyWorkflow):
    """Workflow for detecting and patching vulnerabilities"""

    # Default values for optional arguments
    default_values = {
        "interactive": False,
        "use_helm": False,
        "use_mock_model": False,
        "max_input_tokens": 8192,
        "max_output_tokens": 4096,
        "disable_submit": False,
        "use_cwe": False,
        "include_report_title_in_cwe": False,
    }

    def validate_arguments(self, kwargs):
        """
        Custom validation logic for DetectPatchWorkflow. Checks that:
        1. Required base args are present: task_dir, bounty_number, phase_iterations
        2. Model is required only when not using mock model
        3. Both model and use_mock_model cannot be set simultaneously
        """
        # Check common arguments validation from parent
        super().validate_arguments(kwargs)

        # Check base required arguments
        required_base_args = ["task_dir", "bounty_number", "phase_iterations"]
        missing_args = [arg for arg in required_base_args if arg not in kwargs]
        if missing_args:
            raise ValueError(
                f"Missing required arguments for {self.name}: {', '.join(missing_args)}"
            )

        # Exactly one of (--use_mock_model, --model) should be set
        # Fail if both set
        if kwargs.get("use_mock_model", False) and "model" in kwargs:
            raise ValueError(
                f"Cannot specify both '--model' and '--use_mock_model' simultaneously. "
            )

        # Fail if neither is set
        if not kwargs.get("use_mock_model", False) and "model" not in kwargs:
            raise ValueError(
                f"'--model' argument is required when not using mock model"
            )

    def _create_phases(self):
        """Define and register phases specific to DetectPatchWorkflow."""

        target_host = self.repo_metadata.get("target_host")
        resolved_host = target_host

        phase_kwargs = {
            "use_mock_model": self.params.get("use_mock_model"),
            "model": self.params.get("model"),
            "helm": self.params.get("use_helm"),
            "task_dir": self.task_dir,
            "bounty_number": self.bounty_number,
            "vulnerability_type": self.params.get("vulnerability_type"),
            "task_description": extract_bounty_title(self.task_dir, self.bounty_number),
            "stop_token": STOP_TOKEN,
            "target_host": self.repo_metadata["target_host"],
            "resolved_host": resolved_host,
            "initial_prompt": self.initial_prompt,
            "info": self.repo_metadata.get("info", ""),
            "max_input_tokens": self.params.get("max_input_tokens"),
            "max_output_tokens": self.params.get("max_output_tokens"),
            "interactive": self.interactive,
            "max_iterations": self.params.get("phase_iterations"),
            "submit": not self.params.get("disable_submit", False),
            "use_cwe": self.params.get("use_cwe", False),
            "include_report_title_in_cwe": self.params.get(
                "include_report_title_in_cwe", False
            ),
        }

        if self.params.get("use_cwe", False):
            phase_kwargs["cwe"] = self.bounty_metadata["CWE"]

        if self.params.get("include_report_title", False):
            phase_kwargs["include_report_title_in_cwe"] = self.bounty_metadata["CWE"]

        patch_phase = DetectPatchPhase(workflow=self, **phase_kwargs)

        self._register_root_phase(patch_phase)

    def _get_initial_prompt(self) -> str:
        """
        Provide the initial prompt for the workflow by reading the exploit report.

        Returns:
            str: The formatted initial prompt.
        """

        use_cwe = self.params.get("use_cwe", False)
        has_target_host = bool(self.repo_metadata.get("target_host"))
        add_submit = not self.params.get("disable_submit", False)
        include_report_title = self.params.get("include_report_title_in_cwe", False)

        return build_prompt(
            task_type="detect",
            has_target_host=has_target_host,
            has_cwe=use_cwe,
            with_patch=True,
            add_submit=add_submit,
            include_report_title_in_cwe=include_report_title,
        )
