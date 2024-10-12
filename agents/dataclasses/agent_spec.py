from dataclasses import dataclass

@dataclass
class AgentConfig:
    model: str
    max_output_tokens: int = 4000
    max_input_tokens: int = 2000
    max_iterations: int = 5
    max_response_len: int = 3
    use_helm: bool = False