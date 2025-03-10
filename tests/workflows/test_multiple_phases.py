from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from messages.phase_messages.phase_message import PhaseMessage
from phases.exploit_phase import ExploitPhase
from phases.patch_phase import PatchPhase
from workflows.exploit_patch_workflow import ExploitPatchWorkflow


@pytest.fixture
def mock_workflow():
    with patch("workflows.base_workflow.BaseWorkflow._finalize_workflow"):
        workflow = ExploitPatchWorkflow(
            task_dir=Path("bountybench/setuptools"),
            bounty_number="0",
            model="openai/o3-mini-2025-01-14",
            interactive=False,
            use_mock_model=True,
        )

        with patch.object(workflow.workflow_message, "save", Mock()):
            yield workflow


def test_build_phase_graph(mock_workflow):
    mock_workflow._create_phases()
    mock_workflow._build_phase_graph()

    assert len(mock_workflow.phase_graph) == 2
    assert isinstance(list(mock_workflow.phase_graph.keys())[0], ExploitPhase)
    assert isinstance(list(mock_workflow.phase_graph.keys())[1], PatchPhase)
    assert mock_workflow.phase_graph[list(mock_workflow.phase_graph.keys())[0]] == [
        list(mock_workflow.phase_graph.keys())[1]
    ]
    assert mock_workflow.phase_graph[list(mock_workflow.phase_graph.keys())[1]] == []


@pytest.mark.asyncio
async def test_run_progresses_phases(mock_workflow):
    mock_workflow._create_phases()
    mock_workflow._build_phase_graph()

    # Mock the _run_single_phase method to return a successful PhaseMessage
    successful_phase_message = PhaseMessage("successful_phase")
    successful_phase_message.set_success()
    mock_workflow._run_single_phase = AsyncMock(return_value=successful_phase_message)

    # Run the workflow
    await mock_workflow.run()

    # Check if _run_single_phase was called twice (once for each phase)
    assert mock_workflow._run_single_phase.call_count == 2

    # Check if the calls were made with the correct phases
    calls = mock_workflow._run_single_phase.call_args_list
    assert isinstance(calls[0][0][0], ExploitPhase)
    assert isinstance(calls[1][0][0], PatchPhase)


@pytest.mark.asyncio
async def test_exploit_patch_workflow(mock_workflow):
    # Mock the run method of both ExploitPhase and PatchPhase
    with (
        patch(
            "phases.exploit_phase.ExploitPhase.run", new_callable=AsyncMock
        ) as mock_exploit_run,
        patch(
            "phases.patch_phase.PatchPhase.run", new_callable=AsyncMock
        ) as mock_patch_run,
    ):

        # Set up the mock returns
        exploit_phase_message = PhaseMessage("exploit_phase")
        exploit_phase_message.set_success()
        patch_phase_message = PhaseMessage("patch_phase")
        patch_phase_message.set_success()

        mock_exploit_run.return_value = exploit_phase_message
        mock_patch_run.return_value = patch_phase_message

        # Run the workflow
        await mock_workflow.run()

        # Check if both phases were run
        mock_exploit_run.assert_called_once()
        mock_patch_run.assert_called_once()

        # Check if the workflow completed successfully
        assert mock_workflow.workflow_message.success
        assert mock_workflow.workflow_message.complete


if __name__ == "__main__":
    pytest.main()
