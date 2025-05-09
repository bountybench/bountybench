from pathlib import Path

import pytest

from workflows.exploit_patch_workflow import ExploitPatchWorkflow
from workflows.patch_workflow import PatchWorkflow


class TestWorkflowValidation:
    """Tests for workflow argument validation, focusing on mutually exclusive parameters."""

    def test_patch_workflow_validate_missing_required(self):
        """Test PatchWorkflow validation with missing required arguments."""
        workflow = PatchWorkflow.__new__(
            PatchWorkflow
        )  # Create instance without calling __init__

        # Missing all required args
        with pytest.raises(ValueError, match="Missing required arguments"):
            workflow.validate_arguments({})

        # Missing bounty_number
        with pytest.raises(ValueError, match="Missing required arguments"):
            workflow.validate_arguments(
                {"task_dir": Path("/tmp"), "phase_iterations": 3}
            )

        # Missing task_dir
        with pytest.raises(ValueError, match="Missing required arguments"):
            workflow.validate_arguments({"bounty_number": "1", "phase_iterations": 3})

        # Missing phase_iterations
        with pytest.raises(ValueError, match="Missing required arguments"):
            workflow.validate_arguments(
                {"task_dir": Path("/tmp"), "bounty_number": "1"}
            )

    def test_patch_workflow_validate_model_required(self):
        """Test PatchWorkflow validation with model required."""
        workflow = PatchWorkflow.__new__(PatchWorkflow)

        # No model provided when use_mock_model=False
        with pytest.raises(ValueError, match="'--model' argument is required"):
            workflow.validate_arguments(
                {
                    "task_dir": Path("/tmp"),
                    "bounty_number": "1",
                    "phase_iterations": 3,
                    "use_mock_model": False,
                }
            )

    def test_patch_workflow_validate_mutual_exclusion(self):
        """Test PatchWorkflow validation with mutually exclusive parameters."""
        workflow = PatchWorkflow.__new__(PatchWorkflow)

        # Both model and use_mock_model=True provided
        with pytest.raises(
            ValueError, match="Cannot specify both '--model' and '--use_mock_model'"
        ):
            workflow.validate_arguments(
                {
                    "task_dir": Path("/tmp"),
                    "bounty_number": "1",
                    "phase_iterations": 3,
                    "model": "anthropic/claude-3-opus",
                    "use_mock_model": True,
                }
            )

    def test_patch_workflow_validate_valid_args(self):
        """Test PatchWorkflow validation with valid arguments."""
        workflow = PatchWorkflow.__new__(PatchWorkflow)

        # Valid with model
        workflow.validate_arguments(
            {
                "task_dir": Path("/tmp"),
                "bounty_number": "1",
                "phase_iterations": 3,
                "model": "anthropic/claude-3-opus",
            }
        )

        # Valid with mock model
        workflow.validate_arguments(
            {
                "task_dir": Path("/tmp"),
                "bounty_number": "1",
                "phase_iterations": 3,
                "use_mock_model": True,
            }
        )

    def test_exploit_workflow_validate_missing_required(self):
        """Test ExploitPatchWorkflow validation with missing required arguments."""
        workflow = ExploitPatchWorkflow.__new__(ExploitPatchWorkflow)

        # Missing all required args
        with pytest.raises(ValueError, match="Missing required arguments"):
            workflow.validate_arguments({})

        # Missing bounty_number
        with pytest.raises(ValueError, match="Missing required arguments"):
            workflow.validate_arguments(
                {"task_dir": Path("/tmp"), "phase_iterations": 3}
            )

        # Missing task_dir
        with pytest.raises(ValueError, match="Missing required arguments"):
            workflow.validate_arguments({"bounty_number": "1", "phase_iterations": 3})

        # Missing phase_iterations
        with pytest.raises(ValueError, match="Missing required arguments"):
            workflow.validate_arguments(
                {"task_dir": Path("/tmp"), "bounty_number": "1"}
            )

    def test_exploit_workflow_validate_model_required(self):
        """Test ExploitPatchWorkflow validation with model required."""
        workflow = ExploitPatchWorkflow.__new__(ExploitPatchWorkflow)

        # No model provided when use_mock_model=False
        with pytest.raises(ValueError, match="'--model' is required"):
            workflow.validate_arguments(
                {
                    "task_dir": Path("/tmp"),
                    "bounty_number": "1",
                    "phase_iterations": 3,
                    "use_mock_model": False,
                }
            )

    def test_exploit_workflow_validate_mutual_exclusion(self):
        """Test ExploitPatchWorkflow validation with mutually exclusive parameters."""
        workflow = ExploitPatchWorkflow.__new__(ExploitPatchWorkflow)

        # Both model and use_mock_model=True provided
        with pytest.raises(
            ValueError, match="Cannot specify both '--model' and '--use_mock_model'"
        ):
            workflow.validate_arguments(
                {
                    "task_dir": Path("/tmp"),
                    "bounty_number": "1",
                    "phase_iterations": 3,
                    "model": "anthropic/claude-3-opus",
                    "use_mock_model": True,
                }
            )

    def test_exploit_workflow_validate_valid_args(self):
        """Test ExploitPatchWorkflow validation with valid arguments."""
        workflow = ExploitPatchWorkflow.__new__(ExploitPatchWorkflow)

        # Valid with model
        workflow.validate_arguments(
            {
                "task_dir": Path("/tmp"),
                "bounty_number": "1",
                "phase_iterations": 3,
                "model": "anthropic/claude-3-opus",
            }
        )

        # Valid with mock model
        workflow.validate_arguments(
            {
                "task_dir": Path("/tmp"),
                "bounty_number": "1",
                "phase_iterations": 3,
                "use_mock_model": True,
            }
        )
