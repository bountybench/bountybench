import pytest

from messages.phase_messages.phase_message import PhaseMessage
from messages.workflow_message import WorkflowMessage
from workflows.workflow_context import WorkflowContext, current_workflow_id


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


def test_context_reset_on_exception():
    try:
        with WorkflowContext("failing_workflow"):
            assert current_workflow_id.get() == "failing_workflow"
            raise ValueError("Something went wrong")
    except ValueError:
        pass

    # Context should still be reset
    assert current_workflow_id.get() is None
