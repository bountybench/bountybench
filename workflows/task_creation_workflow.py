from phases.env_setup_phase import EnvSetupPhase
from phases.exploit_phase import ExploitPhase
from prompts.prompts import (
    STOP_TOKEN,
    TASK_CREATION_PROMPT,
)
from resources.utils import read_writeup
from utils.logger import get_main_logger
from workflows.bounty_workflow import BountyWorkflow

logger = get_main_logger(__name__)


class TaskCreationWorkflow(BountyWorkflow):
    """Workflow for setting up the environment and exploiting vulnerabilities"""

    default_values = {
        "interactive": False,
        "use_helm": False,
        "use_mock_model": False,
        "max_input_tokens": 8192,
        "max_output_tokens": 4096,
    }

    def validate_arguments(self, kwargs):
        """
        Custom validation logic for TaskCreationWorkflow. Checks that:
        1. Required base args are present: task_dir, bounty_number, phase_iterations
        2. Model is required only when not using mock model
        3. Both model and use_mock_model cannot be set simultaneously
        """
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
            raise ValueError("Cannot specify both '--model' and '--use_mock_model' simultaneously.")

        # Fail if neither is set
        if not kwargs.get("use_mock_model", False) and "model" not in kwargs:
            raise ValueError("'--model' is required when not using mock model")

    def _create_phases(self):
        """Define and create phases specific to TaskCreationWorkflow."""

        # Superset of parameters for all phases
        phase_kwargs = {
            "use_mock_model": self.params.get("use_mock_model"),
            "model": self.params.get("model"),
            "helm": self.params.get("use_helm"),
            "task_dir": self.task_dir,
            "bounty_number": self.bounty_number,
            "task_description": read_writeup(self.task_dir, self.bounty_number),
            "additional_prompt_information": self.bounty_metadata.get(
                "additional_prompt_information", ""
            ),
            "stop_token": STOP_TOKEN,
            "initial_prompt": self.initial_prompt,
            "info": self.repo_metadata.get("info", "")
            + "\n"
            + self.bounty_metadata.get("info", ""),
            "max_input_tokens": self.params.get("max_input_tokens"),
            "max_output_tokens": self.params.get("max_output_tokens"),
            "interactive": self.interactive,
            "max_iterations": self.params.get("phase_iterations"),
        }

        env_setup_phase = EnvSetupPhase(workflow=self, **phase_kwargs)
        exploit_phase = ExploitPhase(workflow=self, **phase_kwargs)

        self._register_root_phase(env_setup_phase)
        env_setup_phase >> exploit_phase

    def _get_initial_prompt(self):
        """
        Provide the initial prompt for the workflow by reading the exploit report.

        Returns:
            str: The initial prompt.
        """
        return TASK_CREATION_PROMPT
