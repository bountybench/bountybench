import pytest
from datetime import datetime
from pathlib import Path
from messages.phase_messages.phase_message import PhaseMessage
from messages.workflow_message import WorkflowMessage

@pytest.fixture
def workflow_message():
    return WorkflowMessage("test_workflow", workflow_id="test_id", logs_dir="test_logs")

def test_workflow_message_initialization(workflow_message):
    assert workflow_message.workflow_name == "test_workflow"
    assert workflow_message.workflow_id == "test_id"
    assert workflow_message.summary == "incomplete"
    assert len(workflow_message.phase_messages) == 0
    assert workflow_message.agents_used == {}
    assert workflow_message.resources_used == {}
    assert workflow_message.usage == {"input_token": 0, "output_token": 0, "time_taken_in_ms": 0}

def test_set_summary(workflow_message):
    workflow_message.set_summary("completed")
    assert workflow_message.summary == "completed"

def test_add_child_message(workflow_message, mocker):
    mock_phase_message = mocker.Mock(spec=PhaseMessage)
    workflow_message.add_child_message(mock_phase_message)
    assert len(workflow_message.phase_messages) == 1
    mock_phase_message.set_parent.assert_called_once_with(workflow_message)

def test_add_agent(workflow_message):
    mock_agent = type('Agent', (), {'to_dict': lambda self: {'name': 'test_agent'}})()
    workflow_message.add_agent("agent1", mock_agent)
    assert "agent1" in workflow_message.agents_used
    assert workflow_message.agents_used["agent1"] == {'name': 'test_agent'}

def test_add_resource(workflow_message):
    mock_resource = type('Resource', (), {'to_dict': lambda self: {'type': 'test_resource'}})()
    workflow_message.add_resource("resource1", mock_resource)
    assert "resource1" in workflow_message.resources_used
    assert workflow_message.resources_used["resource1"] == {'type': 'test_resource'}

def test_get_total_usage(workflow_message, mocker):
    mock_phase1 = mocker.Mock(spec=PhaseMessage)
    mock_phase1.usage = {"input_token": 10, "output_token": 20, "time_taken_in_ms": 100}
    mock_phase2 = mocker.Mock(spec=PhaseMessage)
    mock_phase2.usage = {"input_token": 15, "output_token": 25, "time_taken_in_ms": 150}
    
    workflow_message._phase_messages = [mock_phase1, mock_phase2]
    
    total_usage = workflow_message.get_total_usage()
    assert total_usage == {
        "total_input_tokens": 25,
        "total_output_tokens": 45,
        "total_time_taken_in_ms": 250
    }

def test_metadata_dict(workflow_message):
    metadata = workflow_message.metadata_dict()
    assert metadata == {
        "workflow_name": "test_workflow",
        "workflow_summary": "incomplete",
        "task": None
    }

def test_to_log_dict(workflow_message):
    log_dict = workflow_message.to_log_dict()
    
    # Check that all expected keys are present
    expected_keys = [
        "workflow_metadata",
        "workflow_usage",
        "phase_messages",
        "agents_used",
        "resources_used",
        "start_time",
        "end_time",
        "workflow_id",
        "additional_metadata"
    ]
    for key in expected_keys:
        assert key in log_dict, f"Expected key '{key}' not found in log_dict"

    # Check specific values
    assert log_dict["workflow_metadata"] == workflow_message.metadata_dict()
    assert log_dict["workflow_usage"] == workflow_message.get_total_usage()
    assert log_dict["phase_messages"] == []  # Assuming no phase messages have been added
    assert log_dict["agents_used"] == {}  # Assuming no agents have been added
    assert log_dict["resources_used"] == {}  # Assuming no resources have been added
    assert log_dict["workflow_id"] == workflow_message.workflow_id
    assert log_dict["additional_metadata"] == workflow_message.additional_metadata

    # Check that start_time is a string (ISO format)
    assert isinstance(log_dict["start_time"], str)
    
    # Check that end_time is None (assuming the workflow hasn't ended)
    assert log_dict["end_time"] is None
