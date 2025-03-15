import asyncio
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from agents.agent_manager import AgentManager
from messages.action_messages.action_message import ActionMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message
from messages.message_handler import MessageHandler
from resources.resource_manager import ResourceManager


@pytest.fixture
def mock_log_message():
    with patch("messages.message_utils.log_message") as mock:
        yield mock


@pytest.fixture
def agent_manager():
    return MagicMock(spec=AgentManager)


@pytest.fixture
def resource_manager():
    return MagicMock(spec=ResourceManager)


@pytest.fixture
def message_handler(agent_manager, resource_manager):
    return MessageHandler(agent_manager, resource_manager)


def test_agent_message_is_message():
    """
    Ensure AgentMessage is a subclass of Message.
    """
    agent_message = AgentMessage("test_id", "test_msg")
    assert isinstance(agent_message, Message)


def test_initialization():
    """
    Test AgentMessage Initialization.
    """
    prev_message = MagicMock(spec=Message)
    agent_message = AgentMessage("test_id", "test_msg", prev_message)

    # Assertions
    assert agent_message.agent_id == "test_id"
    assert agent_message.message == "test_msg"
    assert agent_message.message_type == "AgentMessage"
    assert agent_message.prev is prev_message
    assert agent_message.action_messages == []


@patch("messages.message_utils.broadcast_update")
def test_current_children(mock_broadcast_update, message_handler):
    """
    Test that current_children correctly retrieves the latest versions of actions.
    """
    agent_message = AgentMessage("test_id")
    action_msg1 = ActionMessage("test_id1", "test_msg1")
    action_msg4 = ActionMessage("test_id4", "test_msg4", prev=action_msg1)
    agent_message.add_child_message(action_msg1)
    agent_message.add_child_message(action_msg4)
    action_msg2 = asyncio.run(message_handler.edit_message(action_msg1, "test_msg2"))
    action_msg3 = asyncio.run(message_handler.edit_message(action_msg2, "test_msg3"))
    action_msg5 = asyncio.run(message_handler.edit_message(action_msg4, "test_msg5"))
    action_msg6 = ActionMessage("test_id6", "test_msg6", prev=action_msg3)
    action_msg3.parent.add_child_message(action_msg6)
    org_actions = agent_message.current_children
    parent2 = action_msg2.parent
    parent2_actions = parent2.current_children
    parent3 = action_msg3.parent
    parent3_actions = parent3.current_children
    parent5 = action_msg5.parent
    parent5_actions = parent5.current_children

    # Assertions
    assert len(agent_message.action_messages) == 2
    assert len(org_actions) == 2
    assert org_actions[0] == action_msg1
    assert org_actions[1] == action_msg4
    assert len(parent2.action_messages) == 1
    assert len(parent2_actions) == 1
    assert parent2_actions[0] == action_msg2
    assert len(parent3.action_messages) == 2
    assert len(parent3_actions) == 2
    assert parent3_actions[0] == action_msg3
    assert parent3_actions[1] == action_msg6
    assert len(parent5.action_messages) == 2
    assert len(parent5_actions) == 2
    assert parent5_actions[0] == action_msg5.prev
    assert parent5_actions[1] == action_msg5


def test_add_child_message(mock_log_message):
    """
    Test adding an action message to AgentMessage.
    """
    action_message = MagicMock(spec=ActionMessage)
    agent_message = AgentMessage("test_id")
    agent_message.add_child_message(action_message)

    # Assertions
    assert action_message in agent_message.action_messages
    action_message.set_parent.assert_called_once_with(agent_message)


def test_agent_dict():
    """
    Test broadcast_dict method.
    """
    # Create an action message mock with to_broadcast_dict method
    action_message = MagicMock(spec=ActionMessage)
    action_message.to_broadcast_dict.return_value = {"action": "msg"}

    # Create an agent message and add the mocked action message
    agent_message = AgentMessage("test_id", "test_msg")
    agent_message._action_messages = [action_message]

    # Mock current_children to return our mocked action message
    with patch.object(
        AgentMessage, "current_children", new_callable=PropertyMock
    ) as mock_current_children:
        mock_current_children.return_value = [action_message]
        broadcast_dict = agent_message.to_broadcast_dict()

        # Assertions
        assert broadcast_dict["agent_id"] == "test_id"
        assert broadcast_dict["message"] == "test_msg"
        assert broadcast_dict["current_children"] == [{"action": "msg"}]
        mock_current_children.assert_called_once()
        action_message.to_broadcast_dict.assert_called_once()


def test_to_log_dict():
    """
    Test to_log_dict method.
    """
    action_message = MagicMock(spec=ActionMessage)
    action_message.to_log_dict.return_value = {"action": "msg"}

    agent_message = AgentMessage("test_id", "test_msg")
    agent_message._action_messages = [action_message]

    log_dict = agent_message.to_log_dict()

    # Assertions
    assert log_dict["agent_id"] == "test_id"
    assert log_dict["message"] == "test_msg"
    assert log_dict["action_messages"] == [{"action": "msg"}]
    action_message.to_log_dict.assert_called_once()


def test_iteration_preserved_when_editing(message_handler):
    """
    Test that the iteration is preserved when editing an agent message.
    """
    # Create an agent message with a specific iteration
    agent_message = AgentMessage("test_agent_id", "original message")
    agent_message.set_iteration(3)

    # Edit the message
    edited_message = asyncio.run(
        message_handler.edit_message(agent_message, "edited message")
    )

    # Assert that the iteration is preserved in the edited message
    assert edited_message.iteration == 3
    assert edited_message.message == "edited message"
    assert isinstance(edited_message, AgentMessage)


def test_editing_and_running_preserves_iterations(message_handler, agent_manager):
    """
    Test that when editing messages and running them:
    1. Edited messages preserve their iterations
    2. When running a message, its next message gets iteration+1
    3. Iteration is preserved through the version chain
    """

    # Create async mock for agent run method
    async def create_next_message(*args, **kwargs):
        # Extract the original message from args (expected as a list)
        orig_message = args[0][0]
        # Create a new message with a modified content but preserve agent_id
        result = AgentMessage(
            orig_message.agent_id, f"next from {orig_message.message}"
        )
        return result

    mock_run = MagicMock(side_effect=create_next_message)

    # Set up mock agent
    mock_agent = MagicMock()
    mock_agent.run = mock_run
    agent_manager.get_agent.return_value = mock_agent

    # Create message chain: message_1 (iteration 1) -> message_2 (iteration 2)
    message_1 = AgentMessage("test_agent_id", "message 1")
    message_1.set_iteration(1)

    # Create next placeholder
    next_message = AgentMessage("test_agent_id", "placeholder")
    next_message.set_iteration(2)
    message_1.set_next(next_message)

    # Run to create message_2
    message_2 = asyncio.run(message_handler.run_message(message_1))

    # Verify message_2 has iteration 2
    assert message_2.iteration == 2
    assert message_2.message == "next from message 1"

    # Now edit message_1 to create message_1*
    message_1_edit = asyncio.run(
        message_handler.edit_message(message_1, "edited message 1")
    )

    # Verify message_1* preserved iteration 1
    assert message_1_edit.iteration == 1

    # Run message_1* to create message_2*
    message_2_star = asyncio.run(message_handler.run_message(message_1_edit))

    # Verify message_2* has iteration 2
    assert message_2_star.iteration == 2
    assert message_2_star.message == "next from edited message 1"

    # Edit message_2 to create message_2**
    message_2_star_star = asyncio.run(
        message_handler.edit_message(message_2, "edited message 2")
    )

    # Verify message_2** preserved iteration 2
    assert message_2_star_star.iteration == 2

    # Verify version links
    assert message_1.version_next is message_1_edit
    assert message_1_edit.version_prev is message_1
    assert message_2.version_next is message_2_star_star
    assert message_2_star_star.version_prev is message_2
