from pathlib import Path
import pytest
from unittest.mock import MagicMock
from phases.detect_phase import DetectPhase


def test_detect_phase_raises_if_missing_compatible_patches():
    # Create mocks for the required DetectPhase constructor args
    mock_workflow = MagicMock()
    mock_workflow.bounty_metadata = {}  # missing 'compatible_patches'
    mock_workflow.repo_metadata = {"target_host": "localhost"}  # required for resources
    mock_workflow.task_dir = Path("/tmp/fake_task")
    mock_workflow.bounty_number = 0

    # Minimal extra kwargs expected by BountyPhase/DetectPhase
    kwargs = {
        "workflow": mock_workflow,
        "model": "fake-model",
        "helm": False,
        "use_mock_model": False,
        "params": {},
        "bounty_number": 0,
        "bounty_dir": Path("/tmp/fake_bounty"),
        "tmp_dir": Path("/tmp/tmpdir"),
        "output_agent_files_name": "agent_output",
        "submit": False,
    }

    with pytest.raises(RuntimeError, match="missing 'compatible_patches'"):
        DetectPhase(**kwargs)


def test_detect_phase_succeeds_with_compatible_patches():
    # Create mocks for the required DetectPhase constructor args
    mock_workflow = MagicMock()
    mock_workflow.bounty_metadata = {"compatible_patches": ["0"]}
    mock_workflow.repo_metadata = {"target_host": "localhost"}
    mock_workflow.task_dir = Path("/tmp/fake_task")
    mock_workflow.bounty_number = 0

    # Minimal extra kwargs expected by BountyPhase/DetectPhase
    kwargs = {
        "workflow": mock_workflow,
        "model": "fake-model",
        "helm": False,
        "use_mock_model": False,
        "params": {},
        "bounty_number": 0,
        "bounty_dir": Path("/tmp/fake_bounty"),
        "tmp_dir": Path("/tmp/tmpdir"),
        "output_agent_files_name": "agent_output",
        "submit": False,
    }

    # This should not raise
    phase = DetectPhase(**kwargs)
    assert isinstance(phase, DetectPhase)
