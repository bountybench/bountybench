import pytest
import asyncio
import subprocess
import atexit

from unittest.mock import patch, MagicMock, create_autospec, AsyncMock
from workflows.base_workflow import BaseWorkflow, WorkflowStatus
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

def test_initialization(base_workflow):
    workflow = base_workflow
    assert workflow.status == WorkflowStatus.INCOMPLETE
    assert workflow._current_phase is None
    assert workflow._current_phase_idx == 0
    assert workflow._workflow_iteration_count == 0
    assert workflow.next_iteration_event.is_set() is False
    assert workflow.phase_graph == {}


@pytest.mark.asyncio
async def test_run_single_phase(base_workflow):
    phase_mock = create_autospec(BasePhase, instance=True)
    phase_mock.run = AsyncMock(return_value=PhaseMessage(phase_id="test_phase"))
    phase_mock.agents = []
    phase_mock.resource_manager = MagicMock()

    phase_config_mock = MagicMock()
    phase_config_mock.phase_idx = 0
    phase_mock.phase_config = phase_config_mock

    base_workflow._root_phase = phase_mock
    base_workflow._current_phase = phase_mock
    base_workflow._phase_graph[phase_mock] = []

    message = await base_workflow._run_single_phase(phase_mock, None)
    assert message.phase_id == "test_phase"
    assert base_workflow._workflow_iteration_count == 1


@patch("workflows.base_workflow.BaseWorkflow._run_single_phase", return_value=MagicMock(success=True))
@pytest.mark.asyncio
async def test_run_phases_success(mock_run_phase, base_workflow):
    phase_mock = create_autospec(BasePhase, instance=True)
    phase_mock.agents = []
    
    base_workflow._root_phase = phase_mock
    base_workflow._current_phase = phase_mock
    base_workflow._phase_graph[phase_mock] = []

    base_workflow._current_phase_idx = 0

    async for _ in base_workflow._run_phases():
        continue

    assert base_workflow.status == WorkflowStatus.INCOMPLETE


@patch("workflows.base_workflow.BaseWorkflow._run_single_phase", return_value=MagicMock(success=False))
@pytest.mark.asyncio
async def test_run_phases_failure(mock_run_phase, base_workflow):
    phase_mock = create_autospec(BasePhase, instance=True)
    phase_mock.agents = []

    base_workflow._root_phase = phase_mock
    base_workflow._current_phase = phase_mock

    async for _ in base_workflow._run_phases():
        continue

    assert base_workflow.status == WorkflowStatus.INCOMPLETE


@pytest.mark.asyncio
async def test_run(base_workflow):
    base_workflow._run_phases = MagicMock()
    await base_workflow.run()
    base_workflow._run_phases.assert_called_once()


@pytest.mark.asyncio
async def test_stop(base_workflow):
    """Test the stop functionality."""
    with patch.object(base_workflow.agent_manager, "deallocate_all_agents") as mock_deallocate_agents, \
         patch.object(base_workflow.resource_manager, "deallocate_all_resources") as mock_deallocate_resources, \
         patch.object(base_workflow, "_finalize_workflow") as mock_finalize:

        await base_workflow.stop()
        
        mock_deallocate_agents.assert_called_once()
        mock_deallocate_resources.assert_called_once()
        mock_finalize.assert_called_once()

def test_restart(base_workflow):
    """Test the restart functionality."""
    with patch.object(base_workflow, "_initialize") as mock_initialize, \
         patch.object(base_workflow, "_setup_resource_manager"), \
         patch.object(base_workflow, "_setup_agent_manager"), \
         patch.object(base_workflow, "_setup_interactive_controller"), \
         patch.object(base_workflow, "_compute_resource_schedule"):

        asyncio.run(base_workflow.restart())
        
        mock_initialize.assert_called_once()
        assert base_workflow.status == WorkflowStatus.INCOMPLETE


if __name__ == "__main__":
    pytest.main()