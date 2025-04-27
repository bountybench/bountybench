import asyncio
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, create_autospec, patch

import pytest

from agents.base_agent import IterationFailure
from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message
from messages.phase_messages.phase_message import PhaseMessage
from messages.workflow_message import WorkflowMessage
from phases.base_phase import BasePhase
from workflows.base_workflow import BaseWorkflow


@pytest.fixture
def base_phase():
    class TestBasePhase(BasePhase):
        async def run_one_iteration(
            self,
            phase_message: PhaseMessage,
            agent_instance: Any,
            previous_output: Optional[Message],
        ):
            pass

        def define_resources(self):
            pass

        def define_agents(self):
            pass

        def _get_current_agent(self, get_prev: bool = False):
            return "agent_1", MagicMock()

    # Create a test workflow with an interactive queue
    workflow = MagicMock()
    workflow.next_iteration_queue = asyncio.Queue()
    for i in range(3):
        workflow.next_iteration_queue.put_nowait(f"dummy-{i}")

    workflow.workflow_message = Mock(spec=WorkflowMessage)
    workflow.agent_manager = Mock()
    workflow.resource_manager = Mock()
    return TestBasePhase(workflow)


@pytest.mark.asyncio
async def test_run_iteration_success(base_phase):
    """
    Tests a phase _run_iteration success.
    """
    base_phase._phase_message = PhaseMessage(phase_id="phase_1")
    agent_message = AgentMessage(agent_id="agent_1")

    with patch.object(
        base_phase,
        "run_one_iteration",
        return_value=agent_message,
    ) as mock_run_single_iteration:
        await base_phase._run_iteration()

    assert mock_run_single_iteration.call_count == 1
    assert agent_message in base_phase._phase_message.agent_messages
    assert agent_message.complete is True
    assert agent_message.iteration == 0


@pytest.mark.asyncio
async def test_run_iteration_failure_with_pause(base_phase):
    """
    Tests _run_iteration when IterationFailure is raised and ensures
    _pause_phase correctly sets interactive mode and clears the queue.
    """
    base_phase._phase_message = PhaseMessage(phase_id="phase_1")

    # Make sure there's something in the queue
    assert not base_phase.workflow.next_iteration_queue.empty()

    # Create an agent message for the failure
    agent_message = AgentMessage(agent_id="agent_1")

    with patch.object(
        base_phase,
        "run_one_iteration",
        side_effect=IterationFailure("mocked failure", agent_message),
    ):
        await base_phase._run_iteration()

    assert base_phase.workflow.next_iteration_queue.empty()

    assert agent_message in base_phase._phase_message.agent_messages
    assert agent_message.iteration == 0
    assert agent_message.iteration_time_ms is not None
    assert agent_message.complete is False
    assert base_phase.phase_config.interactive is True


if __name__ == "__main__":
    pytest.main()
