from dataclasses import dataclass

@dataclass
class AgentConfig:
    model: str
    max_output_tokens: int = 4000
    max_input_tokens: int = 2000
    max_iterations: int = 5
    max_iterations_stored_in_memory: int = 3
    use_helm: bool = False