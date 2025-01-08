from dataclasses import dataclass, field

@dataclass
class AgentLMConfig:
    model: str = field(default='openai/o3-mini-2024-12-17')
    max_output_tokens: int = field(default=4096)
    max_input_tokens: int = field(default=4096)
    max_iterations_stored_in_memory: int = field(default=3)
    use_helm: bool = field(default=False)

    @classmethod
    def create(cls, **kwargs):
        return cls(**{k: v for k, v in kwargs.items() if v is not None})

    def __post_init__(self):
        # If 'claude' is in the model name, set use_helm to True
        if 'claude' in self.model.lower():
            self.use_helm = True