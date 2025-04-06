import pytest

from messages.agent_messages.agent_message import AgentMessage
from messages.phase_messages.phase_message import PhaseMessage
from messages.workflow_message import WorkflowMessage
from workflows.workflow_context import (
    PhaseContext,
    WorkflowContext,
    current_phase_id,
    current_workflow_id,
)


@pytest.fixture(autouse=True)
def reset_context():
    # Reset to None before each test
    current_workflow_id.set(None)
    yield
    current_workflow_id.set(None)


def test_workflow_context_sets_and_propagates_to_phase_message():
    workflow_message = WorkflowMessage("workflow_123")
    with WorkflowContext(workflow_message.id):
        assert current_workflow_id.get() == workflow_message.id

        phase_message = PhaseMessage(phase_id="phase_1")
        assert phase_message.parent == workflow_message

    # Back to None after all contexts are exited
    assert current_workflow_id.get() is None


def test_phase_context_sets_and_propagates_to_agent_message():
    workflow_message = WorkflowMessage("workflow_123")
    with WorkflowContext(workflow_message.id):
        phase_message = PhaseMessage(phase_id="phase_1")
        with PhaseContext(phase_message.id):
            assert current_phase_id.get() == phase_message.id

            agent_message = AgentMessage(agent_id="agent_1")
            agent_message2 = AgentMessage(agent_id="agent_2")
            assert agent_message.parent == phase_message
            assert agent_message2.parent == phase_message

        # Back to None after all contexts are exited
        assert current_phase_id.get() is None


def test_phase_context_prevents_incorrect_agent_message_link():
    workflow_message = WorkflowMessage("workflow_123")
    with WorkflowContext(workflow_message.id):
        phase_message = PhaseMessage(phase_id="phase_1")
        with PhaseContext(phase_message.id):
            assert current_phase_id.get() == phase_message.id

            agent_message = AgentMessage(agent_id="agent_1")
            agent_message2 = AgentMessage(agent_id="agent_2", prev=agent_message)

            assert agent_message.parent == phase_message
            assert agent_message2.parent == phase_message

        phase_message2 = PhaseMessage(phase_id="phase_2")
        with PhaseContext(phase_message2.id):
            assert current_phase_id.get() == phase_message2.id

            # First input will be last agent message of prev phase
            agent_message3 = AgentMessage(agent_id="agent_3", prev=agent_message2)
            agent_message4 = AgentMessage(agent_id="agent_4", prev=agent_message3)

            assert agent_message3.parent == phase_message2
            assert agent_message4.parent == phase_message2
            assert agent_message3.prev == None
            assert agent_message2.next == None
            assert agent_message4.prev == agent_message3
            assert agent_message3.next == agent_message4

    # Back to None after all contexts are exited
    assert current_phase_id.get() is None


def test_context_reset_on_exception():
    try:
        with WorkflowContext("failing_workflow"):
            assert current_workflow_id.get() == "failing_workflow"
            raise ValueError("Something went wrong")
    except ValueError:
        pass

    # Context should still be reset
    assert current_workflow_id.get() is None
