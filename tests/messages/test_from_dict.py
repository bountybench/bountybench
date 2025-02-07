import pytest
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.exploit_agent_message import ExploitAgentMessage
from messages.message_utils import message_from_dict

@pytest.fixture
def agent_message_data():
    return {
        "agent_id": "agent-001",
        "message": "Test message",
        "action_messages": [],
        "message_type": "AgentMessage",
        "current_id": "12345",
        "timestamp": "2023-01-01T12:00:00+0000",
    }

@pytest.fixture
def exploit_agent_message_data():
    return {
        "agent_id": "agent-002",
        "message": "Exploit message",
        "success": True,
        "exploit_files_dir": "/path/to/exploit",
        "action_messages": [],
        "message_type": "ExploitAgentMessage",
        "current_id": "67890",
        "timestamp": "2023-01-01T13:00:00+0000",
    }

@pytest.fixture
def action_message_data():
    return {
        "resource_id": "resource-001",
        "message": "Test message",
        "message_type": "ActionMessage",
        "current_id": "54321",
        "next": "9876",
        "timestamp": "2023-01-01T14:00:00+0000",
    }

@pytest.fixture
def command_action_message_data():
    return {
        "resource_id": "resource-002",
        "message": "Command: echo hi",
        "message_type": "CommandMessage",
        "current_id": "9876",
        "prev": "54321",
        "timestamp": "2023-01-01T15:00:00+0000",
    }

def test_agent_message_from_dict(agent_message_data):
    # Create an agent message from the provided dictionary
    agent_message_data.action_messages = [action_message_data, command_action_message_data]

    agent_message = message_from_dict(agent_message_data)

    assert len(agent_message.action_messages) == 2

    action_1 = agent_message.action_messages[0]
    action_2 = agent_message.action_messages[1]

    assert action_1.resource_id == "resource-001"
    assert action_1.next == action_2
    assert action_2.command == "echo hi"
    
def test_agent_message_from_dict(agent_message_data):
    # Create an agent message from the provided dictionary
    agent_message = message_from_dict(agent_message_data)

    # Assertions to ensure properties are set correctly
    assert agent_message.agent_id == "agent-001"
    assert agent_message.message == "Test message"
    assert agent_message.workflow_id is None
    assert agent_message.prev is None
    assert agent_message.next is None
    assert agent_message.timestamp == "2023-01-01T12:00:00+0000"

    # Since there are no action messages, current_actions_list should be empty
    assert agent_message.current_actions_list == []
    assert len(agent_message.action_messages) == 0

def test_exploit_agent_message_from_dict(exploit_agent_message_data):
    # Create an exploit agent message from the provided dictionary
    exploit_agent_message = message_from_dict(exploit_agent_message_data)

    # Assertions to ensure properties are set correctly
    assert exploit_agent_message.agent_id == "agent-002"
    assert exploit_agent_message.message == "Exploit message"
    assert exploit_agent_message.success is True
    assert exploit_agent_message.exploit_files_dir == "/path/to/exploit"
    assert exploit_agent_message.workflow_id is None
    assert exploit_agent_message.prev is None
    assert exploit_agent_message.next is None
    assert exploit_agent_message.timestamp == "2023-01-01T13:00:00+0000"

    # Since there are no action messages, current_actions_list should be empty
    assert exploit_agent_message.current_actions_list == []
    assert len(exploit_agent_message.action_messages) == 0