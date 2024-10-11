from dataclasses import dataclass


@dataclass(frozen=True)
class ModelResponse:
    """
    Dataclass of model response
    """
    content: str
    input_tokens: int
    output_tokens: int
    time_taken_in_ms: float

    @staticmethod
    def from_dict(d: dict) -> "ModelResponse":
        return ModelResponse(d["content"], d["input_tokens"], d["output_tokens"], d["time_taken_in_ms"])
