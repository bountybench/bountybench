import unittest

from messages.answer_message import AnswerMessage
from messages.answer_message_interface import AnswerMessageInterface
from messages.command_message import CommandMessage
from messages.command_message_interface import CommandMessageInterface
from messages.message import Message
from messages.observation import Observation
from resources.utils import run_command


class TestMessageClasses(unittest.TestCase):

    def test_command_message_is_message(self):
        """
        Ensure CommandMessage is a subclass of Message.
        """
        message = CommandMessage("Command: ls")
        self.assertIsInstance(message, Message)

    def test_answer_message_is_message(self):
        """
        Ensure AnswerMessage is a subclass of Message.
        """
        message = AnswerMessage("Answer: 42")
        self.assertIsInstance(message, Message)

    def test_messages_are_not_incorrect_interfaces(self):
        # Ensure that the base Message class is not a CommandMessageInterface.
        message = Message("hi")
        self.assertFalse(isinstance(message, CommandMessageInterface))
        # Ensure that CommandMessage is an instance of CommandMessageInterface.
        command_message = CommandMessage("Command: ls")
        self.assertTrue(isinstance(command_message, CommandMessageInterface))

    def test_command_message_is_not_answer_message_interface(self):
        """
        Ensure that CommandMessage is not an instance of AnswerMessageInterface.
        """
        command_message = CommandMessage("Command: ls")
        self.assertFalse(isinstance(command_message, AnswerMessageInterface))

    def test_answer_message_is_answer_message_interface(self):
        """
        Ensure that AnswerMessage is an instance of AnswerMessageInterface.
        """
        answer_message = AnswerMessage("Answer: 42")
        self.assertTrue(isinstance(answer_message, AnswerMessageInterface))

    def test_command_message_parses_command(self):
        """
        Test that CommandMessage correctly parses the command field.
        """
        message = CommandMessage("Command: ls")
        self.assertEqual(message.command, "ls")

    def test_answer_message_parses_answer(self):
        """
        Test that AnswerMessage correctly parses the answer field.
        """
        message = AnswerMessage("Answer: 42")
        self.assertEqual(message.answer, "42")

    def test_command_message_missing_command_raises_exception(self):
        """
        Ensure an exception is raised if 'Command' is missing from CommandMessage.
        """
        with self.assertRaises(Exception) as context:
            CommandMessage("Answer: 42")
        self.assertEqual(
            str(context.exception),
            "Command is missing from message, cannot be a command message.",
        )

    def test_answer_message_missing_answer_raises_exception(self):
        """
        Ensure an exception is raised if 'answer' is missing from AnswerMessage.
        """
        with self.assertRaises(Exception) as context:
            AnswerMessage("Command: ls")
        self.assertEqual(
            str(context.exception),
            "Answer is missing from message, cannot be a answer message.",
        )

    def test_command_message_set_observation(self):
        """
        Ensure CommandMessage correctly sets and retrieves an observation.
        """
        message = CommandMessage("Command: ls")
        message.set_observation(Observation("Output of ls command"))
        self.assertEqual(message.observation.raw_output, "Output of ls command")

    def test_command_message_observation_not_set_raises_exception(self):
        """
        Ensure an exception is raised if observation is accessed before being set in CommandMessage.
        """
        message = CommandMessage("Command: ls")
        with self.assertRaises(Exception) as context:
            message.observation
        self.assertEqual(
            str(context.exception),
            "Observation is missing or the command has not been executed yet.",
        )

    def test_command_message_parsing_prompt_example(self):
        lm_message_str = "Command:\necho hi"
        message = CommandMessage(lm_message_str)
        self.assertEqual(message.command, "echo hi")


if __name__ == "__main__":
    unittest.main()
