#!/usr/bin/env python3

"""
Helper class for processing JSON logs.
"""

import json
import os
from pathlib import Path

from script_constants import VALID_MODELS


class JSONLog:
    """
    Class for processing and extracting information from JSON log files.
    """

    # Automatically parsed - if this list is insufficient, use self.data to find the values yourself

    workflow_name = None  # data[workflow_metadata][workflow_name]
    workflow_id = None  # data[workflow_id]
    complete = None  # data[workflow_metadata][workflow_summary][complete]
    success = None  # data[workflow_metadata][workflow_summary][success]
    task_dir = None  # data[workflow_metadata][task][task_dir]
    bounty_number = None  # data[workflow_metadata][task][bounty_number]
    task_name = None  # derived from task_dir and bounty_number
    total_input_tokens = None  # data[workflow_usage][total_input_tokens]
    total_output_tokens = None  # data[workflow_usage][total_output_tokens]
    phase_summary = None  # data[phase_messages][phase_summary]
    model_name = None  # data[resources_used][model][config][model]
    helm_run = None  # data[resources_used][model][config][helm]
    model_max_input_tokens = (
        None  # data[resources_used][model][config][max_input_tokens]
    )
    model_max_output_tokens = (
        None  # # data[resources_used][model][config][max_output_tokens]
    )
    severity = None  # data[additional_metadata][bounty_metadata][severity]
    disclosure_bounty = (
        None  # data[additional_metadata][bounty_metadata][disclosure_bounty]
    )
    patch_bounty = None  # data[additional_metadata][bounty_metadata][patch_bounty]
    bountyagent_commit = None  # data[codebase_version]
    bountybench_commit = None  # data[task_codebase_version]

    def __init__(self, filepath):
        """
        Initialize with path to a JSON log file.

        Args:
            filepath (str or Path): Path to the JSON log file
        """
        self.filepath = Path(filepath)
        self.data = None
        self.load()

    def load(self):
        """
        Load the JSON data from the file and extract key fields.

        Returns:
            bool: True if loading was successful, False otherwise
        """
        try:
            with open(self.filepath, "r") as f:
                self.data = json.load(f)

            # Extract all the fields we need from the JSON data
            self._extract_fields()
            return True
        except Exception as e:
            print(f"Error loading {self.filepath}: {e}")
            return False

    def _extract_fields(self):
        """Extract and populate all the class fields from self.data."""
        if not self.data:
            return

        # Extract workflow metadata
        workflow_metadata = self.data.get("workflow_metadata", {})
        self.workflow_name = workflow_metadata.get("workflow_name")
        self.workflow_id = self.data.get("workflow_id")

        # Extract workflow summary
        workflow_summary = workflow_metadata.get("workflow_summary", {})
        self.complete = workflow_summary.get("complete", False)
        self.success = workflow_summary.get("success", False)

        # Extract task information
        task_info = workflow_metadata.get("task", {})
        self.task_dir = task_info.get("task_dir")
        self.bounty_number = task_info.get("bounty_number")

        # Set task_name from task_dir and bounty_number
        if self.task_dir and self.bounty_number:
            task_base = os.path.basename(self.task_dir)
            self.task_name = f"{task_base}_{self.bounty_number}"

        # Extract token usage
        workflow_usage = self.data.get("workflow_usage", {})
        self.total_input_tokens = workflow_usage.get(
            "total_input_tokens", 0
        ) or workflow_usage.get("input_tokens", 0)
        self.total_output_tokens = workflow_usage.get(
            "total_output_tokens", 0
        ) or workflow_usage.get("output_tokens", 0)

        # Extract phase summary
        phases = self.data.get("phase_messages", [])
        if phases:
            self.phase_summary = phases[0].get("phase_summary")

        # Extract model information
        model_config = (
            self.data.get("resources_used", {}).get("model", {}).get("config", {})
        )
        self.model_name = model_config.get("model")
        self.helm_run = model_config.get("helm")
        self.model_max_input_tokens = model_config.get("max_input_tokens")
        self.model_max_output_tokens = model_config.get("max_output_tokens")

        # Extract bounty metadata
        bounty_metadata = self.data.get("additional_metadata", {}).get(
            "bounty_metadata", {}
        )
        self.severity = bounty_metadata.get("severity")
        self.disclosure_bounty = bounty_metadata.get("disclosure_bounty")
        self.patch_bounty = bounty_metadata.get("patch_bounty")

        # Extract commit information
        self.bountyagent_commit = self.data.get("codebase_version")
        self.bountybench_commit = self.data.get("task_codebase_version")

    def identify_issues(self):
        """
        Identify any issues with the log file based on validation criteria.
        Examines workflow completion, success status, and model configuration.
        Uses class variables that were populated during _extract_fields().

        Returns:
            list: List of issues found in the log file
        """
        if self.data is None:
            return ["File could not be loaded"]

        issues = []
        relative_path = os.path.basename(str(self.filepath))

        # Workflow should be complete
        if not self.complete:
            issues.append("Complete is False")

        # Check phases
        if not self.phase_summary:
            issues.append("Phase failed to set up")

        # Check for timeout errors in summary
        if "UnixHTTPConnectionPool(host='localhost', port=None)" in str(self.data):
            issues.append("Unix HTTP timeout issue")

        # Check model configuration
        if not self.model_name:
            issues.append("Missing model")
        elif self.model_name not in VALID_MODELS:
            issues.append(f"Invalid model: {self.model_name}")
        else:
            if self.model_max_output_tokens != VALID_MODELS[self.model_name]:
                issues.append(
                    f"max_output_tokens is {self.model_max_output_tokens}, should be {8192}"
                )

        # Check max_input_tokens
        if self.model_max_input_tokens != 8192:
            issues.append(
                f"max_input_tokens is {self.model_max_input_tokens}, not 8192"
            )

        # Check if task_name was properly set
        if not self.task_name:
            issues.append(
                "Could not determine task_name (missing task_dir or bounty_number)"
            )

        return issues

    def __str__(self):
        """Return a string representation of the JSONLog with all class variables."""
        variables = []
        for var_name, var_value in self.__dict__.items():
            if var_name != "data":  # Skip the data field since it's too large
                variables.append(f"{var_name}: {var_value}")

        # Also include class variables that might not be in __dict__
        class_vars = [
            "workflow_name",
            "workflow_id",
            "complete",
            "success",
            "task_dir",
            "bounty_number",
            "task_name",
            "total_input_tokens",
            "total_output_tokens",
            "summary",
            "model_name",
            "helm_run",
            "model_max_input_tokens",
            "model_max_output_tokens",
            "severity",
            "disclosure_bounty",
            "patch_bounty",
            "bountyagent_commit",
            "bountybench_commit",
        ]

        attributes = []
        for var in class_vars:
            value = getattr(self, var, None)
            if value is not None:
                attributes.append(f"{var}: {value}")

        return f"JSONLog({self.filepath}):\n  " + "\n  ".join(attributes)
