from messages.action_messages.action_message import ActionMessage
from messages.parse_message import parse_field

class AnswerActionMessage(ActionMessage):

    def __init__(self, message: str, resource_id: str, prev: ActionMessage = None) -> None:
        super().__init__(message, prev, resource_id)
        self._answer = self.parse_answer()

    @property
    def answer(self) -> str:
        return self._answer
    
    def parse_answer(self) -> str:
        answer = parse_field(self._message, "Answer: ")
        if not answer:
            raise Exception("Answer is missing from message, cannot be a answer message.")
        return answer

    def to_dict(self) -> dict:
        base_dict = super().to_dict()        
        base_dict.update({
            "response": self.response
        })
        return base_dict