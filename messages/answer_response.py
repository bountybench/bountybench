from responses.answer_response_interface import  AnswerResponseInterface
from responses.parse_response import parse_field

class AnswerResponse(AnswerResponseInterface):
    def __init__(self, response: str) -> None:
        self._response = response
        self._answer = self.parse_answer()
 
    @property
    def response(self) -> str:
        return self._response

    @property
    def answer(self) -> str:
        return self._answer
    
    def parse_answer(self) -> str:
        answer = parse_field(self._response, "Answer: ")
        if not answer:
            raise Exception("Answer is missing from response, cannot be a answer response.")
        return answer

    def to_dict(self) -> dict:
        return {
            "response": self._response,
            "answer": self._answer
        }