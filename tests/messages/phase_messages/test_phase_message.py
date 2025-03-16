from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from agents.agent_manager import AgentManager
from messages.action_messages.action_message import ActionMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message
from messages.message_handler import MessageHandler
from messages.phase_messages.phase_message import PhaseMessage
from messages.workflow_message import WorkflowMessage
from resources.resource_manager import ResourceManager

QUERY_TIME_TAKEN_IN_MS = "query_time_taken_in_ms"
INPUT_TOKEN = "input_token"
OUTPUT_TOKEN = "output_token"


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
    workflow_message.add_child_message(phase_message)

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


def test_add_child_message(mocker, mock_log_message):
    """
    Test adding an AgentMessage to the PhaseMessage.
    """
    mock_action_messages = mocker.patch.object(
        AgentMessage, "action_messages", new_callable=PropertyMock
    )
    action_message = MagicMock(spec=ActionMessage)
    mock_action_messages.return_value = [action_message]
    agent_message = AgentMessage("agent_1")
    phase_message = PhaseMessage("phase_1")
    phase_message.add_child_message(agent_message)

    assert agent_message in phase_message.agent_messages
    assert agent_message.parent == phase_message


@pytest.mark.asyncio
async def test_current_children():
    """
    Test that current_children correctly retrieves the latest versions of agent messages.
    """
    agent_manager = MagicMock(spec=AgentManager)
    resource_manager = MagicMock(spec=ResourceManager)
    message_handler = MessageHandler(agent_manager, resource_manager)

    phase_message = PhaseMessage("phase_1")
    agent_msg1 = AgentMessage("test_id1", "test_msg1")
    agent_msg4 = AgentMessage("test_id4", "test_msg4", prev=agent_msg1)
    phase_message.add_child_message(agent_msg1)
    phase_message.add_child_message(agent_msg4)
    agent_msg2 = await message_handler.edit_message(agent_msg1, "test_msg2")
    agent_msg3 = await message_handler.edit_message(agent_msg2, "test_msg3")
    agent_msg5 = await message_handler.edit_message(agent_msg4, "test_msg5")
    agent_msg6 = AgentMessage("test_id6", "test_msg6", prev=agent_msg3)
    phase_message.add_child_message(agent_msg6)
    current_agents = phase_message.current_children

    assert len(phase_message.agent_messages) == 6
    assert len(current_agents) == 2
    assert current_agents[0] == agent_msg3
    assert current_agents[1] == agent_msg6


def test_to_broadcast_dict(mocker):
    """
    Test the to_broadcast_dict method for PhaseMessage.
    """
    mock_agent_messages = mocker.patch.object(
        PhaseMessage, "agent_messages", new_callable=PropertyMock
    )
    mock_current_children = mocker.patch.object(
        PhaseMessage, "current_children", new_callable=PropertyMock
    )
    mock_super_broadcast = mocker.patch.object(Message, "to_broadcast_dict")

    agent_msg_mock = MagicMock(spec=AgentMessage)
    agent_msg_mock.to_broadcast_dict.return_value = {"agent_key": "agent_value"}
    mock_agent_messages.return_value = [agent_msg_mock]
    mock_current_children.return_value = [agent_msg_mock]
    mock_super_broadcast.return_value = {"super_key": "super_value"}

    phase_message = PhaseMessage("phase_1")
    phase_message.set_summary("summary_1")
    phase_message.add_child_message(agent_msg_mock)

    result_dict = phase_message.to_broadcast_dict()

    assert result_dict["phase_id"] == "phase_1"
    assert result_dict["phase_summary"] == "summary_1"
    assert result_dict["current_children"] is not None
    assert len(result_dict["current_children"]) == 1
    assert result_dict["current_children"][0] == {"agent_key": "agent_value"}
    assert result_dict["super_key"] == "super_value"


def test_calculate_total_usages(mocker):
    """
    Test the calculate_total_usages method accumulates tokens correctly.
    """
    # Create a phase message
    phase_message = PhaseMessage("phase_1")

    # Create mock agent messages with mock action messages
    agent_message1 = MagicMock(spec=AgentMessage)
    agent_message2 = MagicMock(spec=AgentMessage)

    # Create mock action messages with token metadata
    action_message1 = MagicMock(spec=ActionMessage)
    action_message1._additional_metadata = {
        "input_tokens": 100,
        "output_tokens": 50,
        "time_taken_in_ms": 200,
    }

    action_message2 = MagicMock(spec=ActionMessage)
    action_message2._additional_metadata = {
        "input_tokens": 150,
        "output_tokens": 75,
        "time_taken_in_ms": 300,
    }

    action_message3 = MagicMock(spec=ActionMessage)
    action_message3._additional_metadata = {
        "input_tokens": 200,
        "output_tokens": 100,
        "time_taken_in_ms": 400,
    }

    # Action message with incomplete metadata
    action_message4 = MagicMock(spec=ActionMessage)
    action_message4._additional_metadata = {"some_other_field": "value"}

    # Set up the mock agent messages' action_messages property
    agent_message1._action_messages = [action_message1, action_message2]
    agent_message2._action_messages = [action_message3, action_message4]

    # Add agent messages to phase message
    phase_message._agent_messages = [agent_message1, agent_message2]

    # Call the method
    usage = phase_message.calculate_total_usages()

    # Verify the token counts are accumulated correctly
    assert usage[INPUT_TOKEN] == 450  # 100 + 150 + 200
    assert usage[OUTPUT_TOKEN] == 225  # 50 + 75 + 100
    assert usage[QUERY_TIME_TAKEN_IN_MS] == 900  # 200 + 300 + 400

    # Verify the phase's usage property is updated
    assert phase_message.usage == {
        INPUT_TOKEN: 450,
        OUTPUT_TOKEN: 225,
        QUERY_TIME_TAKEN_IN_MS: 900,
    }


def test_to_log_dict(mocker):
    """
    Test the to_log_dict method for PhaseMessage.
    Ensures that it includes agent messages and token usage information.
    """
    # Mock agent_messages property
    mock_agent_messages = mocker.patch.object(
        PhaseMessage, "agent_messages", new_callable=PropertyMock
    )

    # Mock to_log_dict method from parent class
    mock_super_log = mocker.patch.object(
        Message, "to_log_dict", return_value={"super_key": "super_value"}
    )

    # Mock calculate_total_usages method
    mocker.patch.object(
        PhaseMessage,
        "calculate_total_usages",
        return_value={
            INPUT_TOKEN: 500,
            OUTPUT_TOKEN: 250,
            QUERY_TIME_TAKEN_IN_MS: 1000,
        },
    )

    # Create mock agent message
    agent_msg_mock = MagicMock(spec=AgentMessage)
    agent_msg_mock.to_log_dict.return_value = {"agent_key": "agent_value"}
    mock_agent_messages.return_value = [agent_msg_mock]

    # Create and configure PhaseMessage instance
    phase_message = PhaseMessage("phase_1")
    phase_message.set_summary("summary_1")
    phase_message.add_child_message(agent_msg_mock)

    # Get the log dict
    result_dict = phase_message.to_log_dict()

    # Verify phase details
    assert result_dict["phase_id"] == "phase_1"
    assert result_dict["phase_summary"] == "summary_1"

    # Verify agent messages are included
    assert "agent_messages" in result_dict
    assert len(result_dict["agent_messages"]) == 1
    assert result_dict["agent_messages"][0] == {"agent_key": "agent_value"}

    # Verify parent class log data
    assert result_dict["super_key"] == "super_value"

    # Verify token usage information is included
    assert "phase_usage" in result_dict
    assert result_dict["phase_usage"] == {
        INPUT_TOKEN: 500,
        OUTPUT_TOKEN: 250,
        QUERY_TIME_TAKEN_IN_MS: 1000,
    }
