import unittest
from unittest.mock import patch

from messages.action_messages.action_message import ActionMessage
from messages.action_messages.answer_message import AnswerMessage
from messages.action_messages.answer_message_interface import AnswerMessageInterface
from messages.action_messages.command_message import CommandMessage
from messages.action_messages.command_message_interface import CommandMessageInterface
from messages.message import Message
from resources.utils import run_command


@patch("messages.message_utils.log_message")
class TestMessageClasses(unittest.TestCase):

    def test_command_message_is_message(self, mock_log_message):
        """
        Ensure CommandMessage is a subclass of Message.
        """
        message = CommandMessage("test_id", "Command: ls")
        self.assertIsInstance(message, Message)

    def test_answer_message_is_message(self, mock_log_message):
        """
        Ensure AnswerMessage is a subclass of Message.
        """
        message = AnswerMessage("Answer: 42")
        self.assertIsInstance(message, Message)

    def test_messages_are_not_incorrect_interfaces(self, mock_log_message):
        # Ensure that the base Message class is not a CommandMessageInterface.
        message = ActionMessage("test_id", "hi")
        self.assertFalse(isinstance(message, CommandMessageInterface))
        # Ensure that CommandMessage is an instance of CommandMessageInterface.
        command_message = CommandMessage("test_id", "Command: ls")
        self.assertTrue(isinstance(command_message, CommandMessageInterface))

    def test_command_message_is_not_answer_message_interface(self, mock_log_message):
        """
        Ensure that CommandMessage is not an instance of AnswerMessageInterface.
        """
        command_message = CommandMessage("test_id", "Command: ls")
        self.assertFalse(isinstance(command_message, AnswerMessageInterface))

    def test_answer_message_is_answer_message_interface(self, mock_log_message):
        """
        Ensure that AnswerMessage is an instance of AnswerMessageInterface.
        """
        answer_message = AnswerMessage("Answer: 42")
        self.assertTrue(isinstance(answer_message, AnswerMessageInterface))

    def test_command_message_parses_command(self, mock_log_message):
        """
        Test that CommandMessage correctly parses the command field.
        """
        message = CommandMessage("test_id", "Command: ls")
        self.assertEqual(message.command, "ls")

    def test_answer_message_parses_answer(self, mock_log_message):
        """
        Test that AnswerMessage correctly parses the answer field.
        """
        message = AnswerMessage("Answer: 42")
        self.assertEqual(message.answer, "42")

    def test_command_message_missing_command_raises_exception(self, mock_log_message):
        """
        Ensure an exception is raised if 'Command' is missing from CommandMessage.
        """
        with self.assertRaises(Exception) as context:
            CommandMessage("test_id", "Answer: 42")
        self.assertEqual(
            str(context.exception),
            "Command is missing from message, cannot be a command message.",
        )

    def test_answer_message_missing_answer_raises_exception(self, mock_log_message):
        """
        Ensure an exception is raised if 'answer' is missing from AnswerMessage.
        """
        with self.assertRaises(Exception) as context:
            AnswerMessage("Command: ls")
        self.assertEqual(
            str(context.exception),
            "Answer is missing from message, cannot be a answer message.",
        )

    def test_command_message_parsing_prompt_example(self, mock_log_message):
        lm_message_str = "Command:\necho hi"
        message = CommandMessage("test_id", lm_message_str)
        self.assertEqual(message.command, "echo hi")


if __name__ == "__main__":
    unittest.main()
