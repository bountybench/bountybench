from messages.action_messages.action_message import ActionMessage
from messages.action_messages.answer_message_interface import  AnswerMessageInterface
from messages.parse_message import parse_field

class AnswerMessage(AnswerMessageInterface, ActionMessage):
    def __init__(self, message: str) -> None:
        super().__init__(resource_id="", message=message)  
        self._answer = self._parse_answer()

    @property
    def answer(self) -> str:
        return self._answer

    def _parse_answer(self) -> str:
        """Extracts the answer from the message text."""
        answer = parse_field(self.message, "Answer: ")  
        if not answer:
            raise ValueError("Answer is missing from message, cannot be a answer message.")
        return answer

    def action_dict(self) -> dict:
        """Extend the action_dict with the answer field."""
        action_dict = super().action_dict()
        action_dict["answer"] = self.answer
        return action_dict