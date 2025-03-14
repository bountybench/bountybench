import pytest
import asyncio

from unittest.mock import patch, create_autospec, AsyncMock, MagicMock
from workflows.base_workflow import BaseWorkflow
from phases.base_phase import BasePhase
from messages.phase_messages.phase_message import PhaseMessage


@pytest.fixture
def base_workflow():
    class TestBaseWorkflow(BaseWorkflow):
        def _create_phases(self):
            pass

        def _get_initial_prompt(self) -> str:
            return "Initial Prompt"

    return TestBaseWorkflow(interactive=True)


@pytest.mark.asyncio
async def test_run_multiple_phases(base_workflow):
    """
    Tests a workflow run with multiple phases.
    """
    phase_mock_1 = create_autospec(BasePhase, instance=True)
    phase_mock_2 = create_autospec(BasePhase, instance=True)

    base_workflow._root_phase = phase_mock_1
    base_workflow._current_phase = phase_mock_1
    base_workflow._phase_graph[phase_mock_1] = [phase_mock_2]  # Link phases
    base_workflow._current_phase_idx = 0

    phase_message_1 = PhaseMessage(phase_id="phase_1")
    phase_message_1.set_success()  # Phase success, move to next phase
    phase_message_2 = PhaseMessage(phase_id="phase_2", prev=phase_message_1)
    phase_message_2.set_success()  # If last phase fails, workflow_message.success = False

    with patch.object(
        base_workflow,
        "_run_single_phase",
        side_effect=[phase_message_1, phase_message_2],
    ) as mock_run_single_phase:
        async for _ in base_workflow._run_phases():
            continue

    assert mock_run_single_phase.call_count == 2  # All phases should run
    assert base_workflow._current_phase == None  # Last phase should be None
    # assert base_workflow._current_phase_idx == 2 # Currently it is not increasing in base_workflow
    assert base_workflow.workflow_message.complete == True
    assert base_workflow.workflow_message.success == True


@pytest.mark.asyncio
async def test_stop_restart(base_workflow):
    """
    Tests stopping a workflow and restarting.
    """
    phase_mock_1 = create_autospec(BasePhase, instance=True)
    phase_mock_2 = create_autospec(BasePhase, instance=True)

    phase_mock_1.phase_config = MagicMock(phase_idx=1)
    phase_mock_2.phase_config = MagicMock(phase_idx=2)

    base_workflow._root_phase = phase_mock_1
    base_workflow._current_phase = phase_mock_1
    base_workflow._phase_graph[phase_mock_1] = [phase_mock_2]
    base_workflow._current_phase_idx = 0

    phase_message_1 = PhaseMessage(phase_id="phase_1")

    async def stop_phase(*args, **kwargs):
        await base_workflow.stop()  # Stop in the middle of phase
        return

    with patch.object(
        base_workflow, "_run_single_phase", side_effect=stop_phase
    ) as mock_run_single_phase:
        with patch.object(base_workflow, "_handle_workflow_exception", MagicMock()):
            async for _ in base_workflow._run_phases():
                pass

    assert mock_run_single_phase.call_count == 1  # Only phase 1 should run
    assert (
        base_workflow._current_phase == phase_mock_1
    )  # Still at phase 1 because stopped before completed
    assert base_workflow.workflow_message.complete == False

    await base_workflow.restart()

    phase_message_1.set_success()
    phase_message_2 = PhaseMessage(phase_id="phase_2", prev=phase_message_1)
    phase_message_2.set_success()

    with patch.object(
        base_workflow,
        "_run_single_phase",
        side_effect=[phase_message_1, phase_message_2],
    ) as mock_run_single_phase:
        await base_workflow.run_restart()

    assert (
        mock_run_single_phase.call_count == 2
    )  # Both phase 1, 2 should run after restart
    assert base_workflow._current_phase is None
    assert base_workflow.workflow_message.complete
    assert base_workflow.workflow_message.success


if __name__ == "__main__":
    pytest.main()
