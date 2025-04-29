import asyncio
from unittest.mock import MagicMock, PropertyMock, patch
import pytest

from messages.message import Message

#Pulled from test_agent_messages
from agents.agent_manager import AgentManager
from messages.action_messages.action_message import ActionMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.message_handler import MessageHandler
from resources.resource_manager import ResourceManager

@pytest.fixture
def agent_manager():
    return MagicMock(spec=AgentManager)

def test_action_initializaiton():
    """
    Test ActionMessage Initialization
    """
    prev_message = MagicMock(spec=Message)
    action_message = ActionMessage("test_resource_id", "test_msg", {}, prev_message)
    assert action_message._message == "test_msg"
    assert action_message.resource_id == "test_resource_id";
    assert action_message.additional_metadata == {}
    assert action_message.prev is prev_message

@pytest.fixture
def action_message():
    return ActionMessage("test_resource_id", "test_msg")

def test_action_message_is_message(action_message):
    """
    Ensure ActionMessage is a subclass of Message.
    """
    assert isinstance(action_message, Message)

def test_action_setters():
    """
    Tests the setters for the action message:
    - Set message
    - Add additional metadata
    """
    action_message = ActionMessage("test_resource_id", "test_msg")
    action_message.set_message("test_msg2")
    assert(action_message._message == "test_msg2")
    
    action_message.add_to_additional_metadata('test_data_key', 'test_data_value')
    assert(action_message._additional_metadata['test_data_key'] == 'test_data_value')


def test_action_getters(action_message):
    """
    Tests the properties for the action message: getting message, message type, resource id, memory, and metadata
    """
    assert(action_message.message == action_message._message)
    assert(action_message.message_type == "ActionMessage")
    assert(action_message.resource_id == action_message._resource_id)
    assert(action_message.additional_metadata == action_message._additional_metadata)
    assert(action_message.memory == action_message._memory)

def test_action_dict(action_message):
    """
    Tests conversion of action message to a dictionary
    """
    action_dict1 = action_message.action_dict()

    print(action_dict1)

    action_dict2 = {
        "resource_id": "test_resource_id",
        "message": "test_msg",
    }

    assert(action_dict1 == action_dict2)

def test_to_broadcast_dict(action_message):
    """
    Tests the conversion to a broadcast dictionary
    """
    action_message_parent = ActionMessage("parent_id", "parent_msg")
    action_message = ActionMessage("resource_id", "action_msg", prev=action_message_parent)
    
    bcdict = action_message.to_broadcast_dict()

    print(bcdict)
    print(bcdict.keys())

    assert(list(bcdict.keys()) == ['resource_id', 'message', 'message_type', 'prev', 'current_id', 'timestamp'])
    assert(bcdict['resource_id'] == 'resource_id')
    assert(bcdict['message'] == 'action_msg')
    assert(bcdict['resource_id'] == 'resource_id')
    assert(bcdict['current_id'] != bcdict['prev'])

def test_to_log_dict(action_message):
    """
    Tests the conversion to a log dictionary
    """
    action_message_parent = ActionMessage("parent_id", "parent_msg")
    action_message = ActionMessage("resource_id", "action_msg", prev=action_message_parent)
    
    bcdict = action_message.to_log_dict()

    assert(list(bcdict.keys()) == ['resource_id', 'message', 'message_type', 'prev', 'current_id', 'timestamp'])
    assert(bcdict['resource_id'] == 'resource_id')
    assert(bcdict['message'] == 'action_msg')
    assert(bcdict['resource_id'] == 'resource_id')
    assert(bcdict['current_id'] != bcdict['prev'])
