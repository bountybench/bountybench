import pytest
import asyncio
from unittest.mock import MagicMock, patch, PropertyMock
from messages.workflow_message import WorkflowMessage
from messages.phase_messages.phase_message import PhaseMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.action_messages.action_message import ActionMessage
from messages.message import Message
from messages.rerun_manager import RerunManager
from agents.agent_manager import AgentManager
from resources.resource_manager import ResourceManager


@pytest.fixture
def mock_log_message():
    """
    A pytest fixture that patches 'messages.message_utils.log_message'
    so that we don't produce unwanted output during tests.
    """
    with patch("messages.message_utils.log_message") as mock_log:
        yield mock_log


def test_phase_message_is_message():
    """
    Ensure PhaseMessage is a subclass of Message.
    """
    phase_message = PhaseMessage("phase_1")
    assert isinstance(phase_message, Message)


def test_initialization():
    """
    Test PhaseMessage initialization.
    """
    prev_phase = MagicMock(spec=PhaseMessage)
    phase_message = PhaseMessage("phase_1", prev=prev_phase)

    assert phase_message.phase_id == "phase_1"
    assert phase_message.prev == prev_phase
    assert phase_message.success is False
    assert phase_message.complete is False
    assert phase_message.summary == "incomplete"
    assert phase_message.agent_messages == []


def test_workflow_id():
    """
    Test workflow_id property is inherited from the parent (if any).
    """
    workflow_message = WorkflowMessage("workflow_1", "workflow_id")
    phase_message = PhaseMessage("phase_1")
    workflow_message.add_phase_message(phase_message)

    assert phase_message.workflow_id == "workflow_id"


def test_set_success():
    """
    Test setting success to True.
    """
    phase_message = PhaseMessage("phase_1")
    phase_message.set_success()
    assert phase_message.success is True


def test_set_complete():
    """
    Test setting complete to True.
    """
    phase_message = PhaseMessage("phase_1")
    phase_message.set_complete()
    assert phase_message.complete is True


def test_set_summary():
    """
    Test setting the summary.
    """
    phase_message = PhaseMessage("phase_1")
    phase_message.set_summary("summary_1")
    assert phase_message.summary == "summary_1"
    assert phase_message.phase_summary == "summary_1"


def test_add_agent_message(mocker, mock_log_message):
    """
    Test adding an AgentMessage to the PhaseMessage.
    """
    mock_action_messages = mocker.patch.object(
        AgentMessage, 
        'action_messages', 
        new_callable=PropertyMock
    )
    action_message = MagicMock(spec=ActionMessage)
    mock_action_messages.return_value = [action_message]
    agent_message = AgentMessage("agent_1")
    phase_message = PhaseMessage("phase_1")
    phase_message.add_agent_message(agent_message)

    assert agent_message in phase_message.agent_messages
    assert agent_message.parent == phase_message
    log_call_count = 2 + (len(agent_message.action_messages) if agent_message.action_messages else 0)
    assert mock_log_message.call_count == log_call_count


@pytest.mark.asyncio
async def test_current_agent_list():
    """
    Test that current_agent_list correctly retrieves the latest versions of agent messages.
    """
    agent_manager = MagicMock(spec=AgentManager)
    resource_manager = MagicMock(spec=ResourceManager)
    rerun_manager = RerunManager(agent_manager, resource_manager)

    phase_message = PhaseMessage("phase_1")
    agent_msg1 = AgentMessage("test_id1", "test_msg1")
    agent_msg4 = AgentMessage("test_id4", "test_msg4", prev=agent_msg1)
    phase_message.add_agent_message(agent_msg1)
    phase_message.add_agent_message(agent_msg4)
    agent_msg2 = await rerun_manager.edit_message(agent_msg1, "test_msg2")
    agent_msg3 = await rerun_manager.edit_message(agent_msg2, "test_msg3")
    agent_msg5 = await rerun_manager.edit_message(agent_msg4, "test_msg5")
    agent_msg6 = AgentMessage("test_id6", "test_msg6", prev=agent_msg3)
    phase_message.add_agent_message(agent_msg6)
    current_agents = phase_message.current_agent_list
    
    assert len(phase_message.agent_messages) == 6
    assert len(current_agents) == 2
    assert current_agents[0] == agent_msg3
    assert current_agents[1] == agent_msg6


def test_to_dict(mocker):
    """
    Test the to_dict method for PhaseMessage.
    """
    mock_agent_messages = mocker.patch.object(
        PhaseMessage, 
        'agent_messages', 
        new_callable=PropertyMock
    )
    mock_current_agent_list = mocker.patch.object(
        PhaseMessage, 
        'current_agent_list', 
        new_callable=PropertyMock
    )
    mock_super_to_dict = mocker.patch.object(
        Message, 
        'to_dict'
    )
    agent_msg_mock = MagicMock(spec=AgentMessage)
    agent_msg_mock.to_dict.return_value = {"agent_key": "agent_value"}
    mock_agent_messages.return_value = [agent_msg_mock]
    mock_current_agent_list.return_value = [agent_msg_mock]
    mock_super_to_dict.return_value = {"super_key": "super_value"}

    phase_message = PhaseMessage("phase_1")
    phase_message.set_summary("summary_1")
    phase_message.add_agent_message(agent_msg_mock)

    result_dict = phase_message.to_dict()

    assert result_dict["phase_id"] == "phase_1"
    assert result_dict["phase_summary"] == "summary_1"
    assert result_dict["agent_messages"] is not None
    assert len(result_dict["agent_messages"]) == 1
    assert result_dict["agent_messages"][0] == {"agent_key": "agent_value"}

    assert result_dict["current_children"] is not None
    assert len(result_dict["current_children"]) == 1
    assert result_dict["current_children"][0] == {"agent_key": "agent_value"}

    assert result_dict["super_key"] == "super_value"

