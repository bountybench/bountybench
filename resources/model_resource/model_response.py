from dataclasses import dataclass
from typing import Optional

HALLUCINATION_STRINGS = [
    "----------Message from assistant----------",
    "----------Message from system----------",
    "----------Message from assistant",
    "----------</assistant",
    "----------Message from agent",
]


@dataclass(frozen=True)
class ModelResponse:
    """
    Dataclass of model response
    """

    content: str
    input_tokens: int
    output_tokens: int
    time_taken_in_ms: float
    status_code: Optional[int] = None

    def remove_hallucinations(self):
        response = self.content
        response = response.replace("----------Message from agent----------", "")
        for hallucination in HALLUCINATION_STRINGS:
            hallucination_index = response.find(hallucination)
            if hallucination_index != -1:
                response = response[:hallucination_index]
        return response.strip()

    @staticmethod
    def from_dict(d: dict) -> "ModelResponse":
        return ModelResponse(
            d["content"],
            d["input_tokens"],
            d["output_tokens"],
            d["time_taken_in_ms"],
            d.get("status_code"),
        )

    def to_dict(self):
        result = {
            "content": self.content,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "time_taken_in_ms": self.time_taken_in_ms,
        }
        if self.status_code is not None:
            result["status_code"] = self.status_code
        return result
