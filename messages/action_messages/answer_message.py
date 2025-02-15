from messages.action_messages.action_message import ActionMessage
from messages.action_messages.answer_message_interface import  AnswerMessageInterface
from messages.parse_message import parse_field

class AnswerMessage(AnswerMessageInterface, ActionMessage):
    def __init__(self, message: str) -> None:
        self._message = message
        self._answer = self.parse_answer()
 
    @property
    def message(self) -> str:
        return self._message

    @property
    def answer(self) -> str:
        return self._answer
    
    def parse_answer(self) -> str:
        answer = parse_field(self._message, "Answer: ")
        if not answer:
            raise Exception("Answer is missing from message, cannot be a answer message.")
        return answer

    def to_log_dict(self) -> dict:
        base_dict = super(ActionMessage, self).to_log_dict() 
        action_dict = self.action_dict()
        action_dict.update({
            "answer": self.answer
        })
        action_dict.update(base_dict)
        return action_dict

    def to_broadcast_dict(self) -> dict:
        base_dict = super(ActionMessage, self).to_broadcast_dict() 
        action_dict = self.action_dict()
        action_dict.update({
            "answer": self.answer
        })
        action_dict.update(base_dict)
        return action_dict