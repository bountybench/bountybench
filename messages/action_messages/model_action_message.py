from typing import Optional
from messages.action_messages.action_message import ActionMessage


"""

class ModelActionMessage(ActionMessage):
    def __init__(self, message: str, resource_id: str, response: str, prev: ActionMessage = None) -> None:
        super().__init__(message, prev, resource_id)
        self._response = response

    @property
    def response(self) -> bool:
        return self._response
    
    def to_dict(self) -> dict:
        base_dict = super().to_dict()        
        base_dict.update({
            "response": self.response
        })
        return base_dict
    
"""




class ModelActionMessage(ActionMessage):
    """Represents a model's response as an action message"""
    def __init__(
        self, 
        message: str,  # The input prompt
        resource_id: str,
        prev: Optional['ActionMessage'] = None,
        response: str = "",  
        input_tokens: int = 4096,
        output_tokens: int = 4096,
        time_taken_ms: float = 0.0
    ) -> None:
        super().__init__(message, resource_id, prev)
        
        
        self._response = response
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self._time_taken_ms = time_taken_ms

    @property
    def response(self) -> str:
        return self._response

    @property
    def input_tokens(self) -> int:
        return self._input_tokens

    @property
    def output_tokens(self) -> int:
        return self._output_tokens

    @property
    def time_taken_ms(self) -> float:
        return self._time_taken_ms

    def remove_hallucinations(self) -> str:
        """Remove hallucination strings from response"""
        HALLUCINATION_STRINGS = [
            "----------Message from assistant----------",
            "----------Message from system----------",
            "----------Message from assistant",
            "----------</assistant",
            "----------Message from agent",
        ]
        
        cleaned_response = self.response
        cleaned_response = cleaned_response.replace("----------Message from agent----------", "")
        for hallucination in HALLUCINATION_STRINGS:
            hallucination_index = cleaned_response.find(hallucination)
            if hallucination_index != -1:
                cleaned_response = cleaned_response[:hallucination_index]
        
        return cleaned_response.strip()
    
    def to_dict(self) -> dict:
        base_dict = super().to_dict()
        
        base_dict.update({
            "response": self.response,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "time_taken_ms": self.time_taken_ms
        })
        return base_dict