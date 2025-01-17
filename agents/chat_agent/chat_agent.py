from dataclasses import dataclass
from typing import List, Optional

from agents.base_agent import AgentConfig, BaseAgent
from agents.dataclasses.agent_lm_spec import AgentLMConfig
from agents.prompts import STOP_TOKEN
from agents.utils import truncate_input_to_max_tokens
from resources.model_resource.model_response import ModelResponse
from models.query import query
from resources.resource_manager import ResourceManager
from messages.message import Message
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

TIMEOUT_PER_COMMAND = 120
MAX_RETRIES = 3
RETRY_DELAY = 30
TEMPERATURE = 0.5

@dataclass
class ChatAgentConfig(AgentConfig):
    lm_config: AgentLMConfig


class ChatAgent(BaseAgent):
    memory: List[str] = []

    # Switch from listing just resource classes to (ResourceClass, "attr_name").
    # BaseAgent will do: self.init_files = resource_manager.get_resource("init_files")
    # etc.
    REQUIRED_RESOURCES = []
    OPTIONAL_RESOURCES = []
    ACCESSIBLE_RESOURCES = []
    def __init__(self, agent_id: str, agent_config: ChatAgentConfig):
        """
        Args:
            agent_config: ChatAgentConfig containing model.
            resource_manager: ResourceManager instance responsible for managing resources.
        """
        # Pass the agent_config and resource_manager to BaseAgent
        super().__init__(agent_id, agent_config)

        # Initialize specific attributes
        self.initial_prompt = "You are a helpful chatbot."
        self.prompt = self.initial_prompt

    async def modify_memory_and_run(self, input: str) -> None:
        self.initial_prompt = input
        self.memory = [] #overwrites all previous memory

        result = await self.run([])
        print("Finished run")
        return result
    
    async def run(self, messages: List[Message]) -> Message:
        print("In run")
        if len(messages) > 1:
            raise Exception(f"Accepts at most a single message, got {len(messages)}.")

        if len(messages) == 0:        
            self.formulate_prompt()
        else:
            message = messages[0]
            self.formulate_prompt(message)

        chat_message = self.execute()
        self._update_memory(chat_message)

        return chat_message

    def _update_memory(self, message: Message) -> None:
        if len(self.memory) >= self.agent_config.lm_config.max_iterations_stored_in_memory:
            self.memory = self.memory[1:] + [message.message]
        else:
            self.memory.append(message.message)

    def formulate_prompt(self, message: Optional[Message] = None) -> str:
        """
        Formulates the prompt, including the truncated memory.
        """
        if message:
            if self.initial_prompt:
                self._update_memory(message)
            else:
                self.initial_prompt = message.message
        

        truncated_input = truncate_input_to_max_tokens(
            max_input_tokens=self.agent_config.lm_config.max_input_tokens,
            model_input="\n".join(self.memory),
            model=self.agent_config.lm_config.model,
            use_helm=self.agent_config.lm_config.use_helm,
        )
        prompt = self.initial_prompt + truncated_input
        self.prompt = prompt
        return prompt

    def execute(self) -> Message:
        lm_executor_message = self.call_lm()
        return lm_executor_message

    def _parse_message(self, message: str) -> Message:
        """
        Attempts to parse the raw model string into either AnswerMessage or CommandMessage.
        """
        return Message(message)
    
    def call_lm(self) -> Message:
        """
        Calls the language model and ensures the message is in valid format.
        Retries up to MAX_RETRIES if the message is invalid.
        """
        model_input = self.prompt
        iterations = 0
        while iterations < MAX_RETRIES:
            model_message: ModelResponse = query(
                model=self.agent_config.lm_config.model,
                message=model_input,
                temperature=TEMPERATURE,
                max_tokens=self.agent_config.lm_config.max_output_tokens,
                stop_sequences=[STOP_TOKEN],
                helm=self.agent_config.lm_config.use_helm
            )

            model_message = model_message.remove_hallucinations()
            lm_message = model_message + f"\n{STOP_TOKEN}"

            try:
                return self._parse_message(lm_message)
            except Exception as e:
                logger.warning(f"Retrying {iterations}/{MAX_RETRIES} after parse error: {e}")
                iterations += 1

        raise Exception("call_lm error: Max retries reached without valid message.")

    def to_dict(self) -> dict:
        """
        Serializes the ChatAgent state to a dictionary.
        """
        return {
            "config": self.agent_config.lm_config.__dict__,
            "memory": self.memory,
            "initial_prompt": self.initial_prompt,
            "prompt": self.prompt,
            "timestamp": getattr(self, "timestamp", None),
        }

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> "ChatAgent":
        """
        Creates an ExecutorAgent instance from a serialized dictionary.
        """
        config = AgentLMConfig(**data["config"])
        agent = cls(
            config=config,
            initial_prompt=data["initial_prompt"],
            **kwargs
        )
        agent.memory = data["memory"]
        agent.prompt = data["prompt"]
        if data.get("timestamp"):
            agent.timestamp = data["timestamp"]
        return agent

    def save_to_file(self, filepath: str) -> None:
        """
        Saves the agent state to a JSON file, adding a timestamp.
        """
        import json
        from datetime import datetime

        state = self.to_dict()
        state["timestamp"] = datetime.now().isoformat()

        with open(filepath, "w") as f:
            json.dump(state, f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str, **kwargs) -> "ChatAgent":
        """
        Loads an agent state from a JSON file and reconstructs it.
        """
        import json

        with open(filepath, "r") as f:
            data = json.load(f)
        return cls.from_dict(data, **kwargs)