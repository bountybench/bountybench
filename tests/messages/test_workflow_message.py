import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from messages.phase_messages.phase_message import PhaseMessage
from messages.workflow_message import WorkflowMessage

# Constants
QUERY_TIME_TAKEN_IN_MS = "query_time_taken_in_ms"
INPUT_TOKEN = "input_token"
OUTPUT_TOKEN = "output_token"

def test_get_total_usage():
    """
    Test the get_total_usage method to ensure it correctly aggregates token usage.
    """
    phase_message_1 = MagicMock(spec=PhaseMessage)
    phase_message_1.usage = {INPUT_TOKEN: 300, OUTPUT_TOKEN: 150, QUERY_TIME_TAKEN_IN_MS: 500}
    
    phase_message_2 = MagicMock(spec=PhaseMessage)
    phase_message_2.usage = {INPUT_TOKEN: 200, OUTPUT_TOKEN: 100, QUERY_TIME_TAKEN_IN_MS: 700}
    
    workflow_message = WorkflowMessage("test_workflow")
    workflow_message._phase_messages = [phase_message_1, phase_message_2]
    
    usage = workflow_message.get_total_usage()
    
    assert usage == {
        "total_input_tokens": 500,
        "total_output_tokens": 250,
        "total_query_time_taken_in_ms": 1200
    }
    assert workflow_message.usage == usage

def test_to_log_dict(mocker):
    """
    Test that to_log_dict includes workflow usage information.
    """
    mock_phase = mocker.patch.object(WorkflowMessage, "phase_messages", new_callable=PropertyMock, return_value=[])
    mock_metadata = mocker.patch.object(WorkflowMessage, "metadata_dict", return_value={"key": "value"})
    mock_usage = mocker.patch.object(WorkflowMessage, "get_total_usage", return_value={
        "total_input_tokens": 500,
        "total_output_tokens": 250,
        "total_query_time_taken_in_ms": 1000
    })
    
    workflow_message = WorkflowMessage("test_workflow")
    log_dict = workflow_message.to_log_dict()
    
    assert "workflow_usage" in log_dict
    assert log_dict["workflow_usage"] == {
        "total_input_tokens": 500,
        "total_output_tokens": 250,
        "total_query_time_taken_in_ms": 1000
    }
