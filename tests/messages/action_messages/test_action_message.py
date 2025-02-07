import pytest

from messages.action_messages.action_message import ActionMessage


@pytest.fixture
def action_message():
    resource_id = "res-123"
    message = "Test action"
    additional_metadata = {"key": "value"}

    return ActionMessage(
        resource_id=resource_id,
        message=message,
        additional_metadata=additional_metadata,
    )


def test_initialization(action_message):
    assert action_message.resource_id == "res-123"
    assert action_message.message == "Test action"
    assert action_message.additional_metadata == {"key": "value"}
    assert action_message.message_type == "ActionMessage"


def test_action_dict(action_message):
    expected_dict = {
        "resource_id": "res-123",
        "message": "Test action",
        "additional_metadata": {"key": "value"},
    }
    assert action_message.action_dict() == expected_dict


def test_to_dict(action_message):
    action_dict = action_message.to_dict()
    assert "resource_id" in action_dict
    assert "message" in action_dict
    assert "additional_metadata" in action_dict
    assert "timestamp" in action_dict


def test_from_dict():
    data = {
        "resource_id": "res-123",
        "message": "Test action",
        "additional_metadata": {"key": "value"},
        "prev": None,
        "next": None,
        "version_prev": None,
        "version_next": None,
        "parent": None,
        "current_id": None,
        "timestamp": 1234567890,
    }
    action_msg = ActionMessage.from_dict(data)

    assert action_msg.resource_id == "res-123"
    assert action_msg.message == "Test action"
    assert action_msg.additional_metadata == {"key": "value"}
