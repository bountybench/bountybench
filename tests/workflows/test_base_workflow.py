import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.agent_manager import AgentManager
from messages.message import Message
from messages.phase_messages.phase_message import PhaseMessage
from messages.rerun_manager import RerunManager
from messages.workflow_message import WorkflowMessage
from phases.base_phase import BasePhase
from resources.resource_manager import ResourceManager
from workflows.base_workflow import BaseWorkflow, WorkflowStatus


# ---- MOCK CLASSES ----
class MockPhase(BasePhase):
    """Mock class for BasePhase."""

    def define_agents(self):
        return {}

    def define_resources(self):
        return {}

    def run_one_iteration(self, phase_message, agent_instance, previous_output):
        return MagicMock()

    def _initialize_agents(self):
        """Override to avoid agent initialization for testing"""
        pass


class TestWorkflow(BaseWorkflow):
    """Mock class for BaseWorkflow."""

    def _create_phases(self):
        phase1 = MockPhase(workflow=self)
        phase2 = MockPhase(workflow=self)
        phase3 = MockPhase(workflow=self)

        phase1 >> phase2 >> phase3
        self._register_root_phase(phase1)

    def _get_initial_prompt(self):
        return "Test Prompt"


# ---- FIXTURE FOR WORKFLOW ----
@pytest.fixture
def base_workflow():
    """Fixture to initialize BaseWorkflow instance."""
    return TestWorkflow()


# ---- TESTING WORKFLOW INITIALIZATION ----
def test_base_workflow_initialization(base_workflow):
    """Test if BaseWorkflow initializes correctly."""
    assert isinstance(base_workflow.workflow_message, WorkflowMessage)
    assert base_workflow.status == WorkflowStatus.INCOMPLETE
    assert base_workflow._workflow_iteration_count == 0


# ---- TESTING PHASE GRAPH CREATION ----
def test_phase_graph_creation(base_workflow):
    """Test if workflow graph and phase connections are set up correctly."""
    phases = list(base_workflow._phase_graph.keys())

    assert len(phases) == 3
    assert base_workflow._root_phase == phases[0]

    # Test phase connections
    assert len(base_workflow._phase_graph[phases[0]]) == 1
    assert base_workflow._phase_graph[phases[0]][0] == phases[1]
    assert base_workflow._phase_graph[phases[1]][0] == phases[2]


# ---- TESTING WORKFLOW RUN ----
@pytest.mark.asyncio
async def test_workflow_run(base_workflow):
    """Test that BaseWorkflow runs successfully."""
    base_workflow._run_phases = AsyncMock(return_value=iter([]))  # Mock async generator
    await base_workflow.run()
    base_workflow._run_phases.assert_called_once()


# ---- TESTING RESOURCE & AGENT MANAGER SETUP ----
@patch("workflows.base_workflow.ResourceManager")
@patch("workflows.base_workflow.AgentManager")
def test_workflow_managers(mock_agent_manager, mock_resource_manager, base_workflow):
    """Test if agent and resource managers are set up correctly."""
    base_workflow._setup_agent_manager()
    base_workflow._setup_resource_manager()
    base_workflow._setup_rerun_manager()

    assert isinstance(base_workflow.agent_manager, AgentManager)
    assert isinstance(base_workflow.resource_manager, ResourceManager)
    assert isinstance(base_workflow.rerun_manager, RerunManager)


# ---- TESTING PHASE REGISTRATION ----
def test_register_phase(base_workflow):
    """Test phase registration in workflow."""
    phase_mock = MagicMock(spec=BasePhase)
    base_workflow.register_phase(phase_mock)
    assert phase_mock in base_workflow._phase_graph


def test_register_root_phase(base_workflow):
    """Test registering root phase."""
    phase_mock = MagicMock(spec=BasePhase)
    base_workflow._register_root_phase(phase_mock)
    assert base_workflow._root_phase == phase_mock
    assert phase_mock in base_workflow._phase_graph


# ---- TESTING MAX ITERATIONS LIMIT ----
def test_max_iterations_check(base_workflow):
    """Test if workflow correctly detects max iteration limit."""
    base_workflow._workflow_iteration_count = base_workflow.max_iterations
    assert base_workflow._max_iterations_reached() is True


# ---- TESTING ERROR HANDLING ----
def test_handle_workflow_exception(base_workflow):
    """Test exception handling in workflow."""
    with pytest.raises(Exception, match="Test Exception"):
        base_workflow._handle_workflow_exception(Exception("Test Exception"))


# ---- TESTING ASYNC PHASE EXECUTION ----
@pytest.mark.asyncio
async def test_run_single_phase():
    """Test running a single phase."""
    base_workflow = MagicMock(spec=BaseWorkflow)
    phase_mock = MagicMock(spec=BasePhase)
    phase_mock.agents = []
    phase_mock.resource_manager._resources.id_to_resource = {}

    phase_message_mock = MagicMock(spec=PhaseMessage)
    phase_message_mock.success = True

    phase_mock.run = AsyncMock(return_value=phase_message_mock)

    result = await BaseWorkflow._run_single_phase(base_workflow, phase_mock, None)
    assert isinstance(result, PhaseMessage)


# ---- TESTING ASYNC USER INTERACTIONS ----
@pytest.mark.asyncio
async def test_add_user_message():
    """Test user message addition."""
    base_workflow = MagicMock(spec=BaseWorkflow)
    base_workflow._current_phase.add_user_message = AsyncMock(
        return_value="User response"
    )

    result = await BaseWorkflow.add_user_message(base_workflow, "Hello")
    assert result == "User response"
    base_workflow.next_iteration_event.set.assert_called_once()


@pytest.mark.asyncio
async def test_get_last_message():
    """Test retrieving last message."""
    base_workflow = MagicMock(spec=BaseWorkflow)
    message_mock = MagicMock()
    message_mock.message = "Last Message"

    base_workflow._current_phase.last_agent_message = message_mock
    result = await BaseWorkflow.get_last_message(base_workflow)

    assert result == "Last Message"


# ---- TESTING WORKFLOW FINALIZATION ----
@pytest.mark.asyncio
async def test_workflow_stop():
    """Test stopping the workflow."""
    base_workflow = MagicMock(spec=BaseWorkflow)
    base_workflow.agent_manager = MagicMock()
    base_workflow.resource_manager = MagicMock()

    await BaseWorkflow.stop(base_workflow)

    assert base_workflow.status == WorkflowStatus.INCOMPLETE
    base_workflow.agent_manager.deallocate_all_agents.assert_called_once()
    base_workflow.resource_manager.deallocate_all_resources.assert_called_once()


# ---- TESTING TOGGLE VERSION ----
@pytest.mark.asyncio
async def test_toggle_version():
    """Test toggling message versions."""
    base_workflow = MagicMock(spec=BaseWorkflow)
    message_mock = MagicMock(spec=Message)
    message_mock.version_prev = MagicMock()
    message_mock.version_next = MagicMock()

    base_workflow.workflow_message.workflow_id = "test_id"
    message_dict["test_id"] = {"message_1": message_mock}

    result = await BaseWorkflow.toggle_version(base_workflow, "message_1", "prev")
    assert result is not None

    result = await BaseWorkflow.toggle_version(base_workflow, "message_1", "next")
    assert result is not None


# ---- RUN TESTS ----
if __name__ == "__main__":
    pytest.main()
