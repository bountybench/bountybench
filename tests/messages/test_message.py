from unittest.mock import patch

import pytest

from messages.action_messages.action_message import ActionMessage
from messages.action_messages.answer_message import AnswerMessage
from messages.action_messages.answer_message_interface import AnswerMessageInterface
from messages.action_messages.command_message import CommandMessage
from messages.action_messages.command_message_interface import CommandMessageInterface
from messages.message import Message
from messages.parse_message import parse_field
from resources.base_resource import BaseResource


class MockResource(BaseResource):
    def __init__(self, resource_id, resource_config):
        super().__init__(resource_id, resource_config)

    def stop(self):
        pass


@patch("messages.message_utils.log_message")
def test_command_message_is_message(mock_log_message):
    message = CommandMessage("test_id", "Command: ls")
    assert isinstance(message, Message)


@patch("messages.message_utils.log_message")
def test_answer_message_is_message(mock_log_message):
    message = AnswerMessage("Answer: 42")
    assert isinstance(message, Message)


@patch("messages.message_utils.log_message")
def test_messages_are_not_incorrect_interfaces(mock_log_message):
    message = ActionMessage("test_id", "hi")
    assert not isinstance(message, CommandMessageInterface)
    command_message = CommandMessage("test_id", "Command: ls")
    assert isinstance(command_message, CommandMessageInterface)


@patch("messages.message_utils.log_message")
def test_command_message_is_not_answer_message_interface(mock_log_message):
    command_message = CommandMessage("test_id", "Command: ls")
    assert not isinstance(command_message, AnswerMessageInterface)


@patch("messages.message_utils.log_message")
def test_answer_message_is_answer_message_interface(mock_log_message):
    answer_message = AnswerMessage("Answer: 42")
    assert isinstance(answer_message, AnswerMessageInterface)


@patch("messages.message_utils.log_message")
def test_command_message_parses_command(mock_log_message):
    message = CommandMessage("test_id", "Command: ls")
    assert message.command == "ls"


@patch("messages.message_utils.log_message")
def test_answer_message_parses_answer(mock_log_message):
    message = AnswerMessage("Answer: 42")
    assert message.answer == "42"


@patch("messages.message_utils.log_message")
def test_command_message_missing_command_raises_exception(mock_log_message):
    with pytest.raises(Exception) as context:
        CommandMessage("test_id", "Answer: 42")
    assert (
        str(context.value)
        == "Command is missing from message, cannot be a command message."
    )


@patch("messages.message_utils.log_message")
def test_answer_message_missing_answer_raises_exception(mock_log_message):
    with pytest.raises(Exception) as context:
        AnswerMessage("Command: ls")
    assert (
        str(context.value)
        == "Answer is missing from message, cannot be a answer message."
    )


@patch("messages.message_utils.log_message")
def test_command_message_parsing_prompt_example(mock_log_message):
    lm_message_str = "Command:\necho hi"
    message = CommandMessage("test_id", lm_message_str)
    assert message.command == "echo hi"


def test_command_message_parsing_multiple_fields_example():
    message = """" \
Log:
1. Command: grep -R 'redirect(' codebase/gradio - identified potential redirect in oauth.py, but not directly handling the vulnerability.

Command:
grep -R 'file=' codebase/gradio
<END>" \
"""
    # Last instance of field
    command = parse_field(message, "Command:", stop_str="<END>")
    assert command == "grep -R 'file=' codebase/gradio"

    # First instance of field
    command = parse_field(message, "Command:", stop_str="<END>", from_end=False)
    assert (
        command
        == """grep -R 'redirect(' codebase/gradio - identified potential redirect in oauth.py, but not directly handling the vulnerability.

Command:
grep -R 'file=' codebase/gradio"""
    )
