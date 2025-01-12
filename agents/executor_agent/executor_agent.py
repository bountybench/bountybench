from dataclasses import dataclass, field
from typing import List, Optional

from agents.base_agent import AgentConfig, BaseAgent
from agents.dataclasses.agent_lm_spec import AgentLMConfig
from agents.executor_agent.prompt import STOP_TOKEN
from agents.utils import truncate_input_to_max_tokens
from models.model_response import ModelResponse
from models.query import query
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.setup_resource import SetupResource
from messages.answer_message import AnswerMessage
from messages.command_message import CommandMessage
from messages.command_message_interface import CommandMessageInterface
from messages.observation import Observation
from messages.message import Message
from utils.logger import get_main_logger
from utils.progress_logger import start_progress, stop_progress

logger = get_main_logger(__name__)

TIMEOUT_PER_COMMAND = 120
MAX_RETRIES = 3
RETRY_DELAY = 30
TEMPERATURE = 0.5

@dataclass
class ExecutorAgentConfig(AgentConfig):
    lm_config: AgentLMConfig = field(default_factory=AgentLMConfig)
    target_host: str = field(default='')
    initial_prompt: Optional[str] = field(default=None)

class ExecutorAgent(BaseAgent):
    memory: List[str] = []

    REQUIRED_RESOURCES = [
       (InitFilesResource, "init_files"),
        (KaliEnvResource, "kali_env")
    ]
    OPTIONAL_RESOURCES = [(SetupResource, "repo_resource"), (SetupResource, "task_server")]
    ACCESSIBLE_RESOURCES = [
        (KaliEnvResource, "kali_env"),
       (InitFilesResource, "init_files"),
        (SetupResource, "repo_resource"),
        (SetupResource, "task_server")
    ]
    
    def __init__(self, agent_id, agent_config: ExecutorAgentConfig):#, resource_manager: ResourceManager):
        """
        Args:
            agent_config: ExecutorAgentConfig containing model, initial prompt, and target host.
            resource_manager: ResourceManager instance responsible for managing resources.
        """
        # Pass the agent_config and resource_manager to BaseAgent
        super().__init__(agent_id, agent_config)

        # Initialize specific attributes
        if hasattr(agent_config, "initial_prompt"):
            self.initial_prompt = agent_config.initial_prompt
        self.prompt = self.initial_prompt

        # If a target_host is provided, run health_check on self.kali_env
        self.target_host = agent_config.target_host

        #if self.target_host: 
            #self.kali_env.health_check(self.target_host)
        
    def run(self, messages: List[Message]) -> Message:
        if len(messages) > 1:
            raise Exception(f"Accepts at most a single message, got {len(messages)}.")

        if len(messages) == 0:        
            self.formulate_prompt()
        else:
            message = messages[0]
            self.formulate_prompt(message)

        executor_message = self.execute()
        self._update_memory(executor_message)

        return executor_message

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
        # If the model decides to output a command, we run it in the environment
        logger.info(f"LM Response:\n{lm_executor_message.message}")
        if issubclass(lm_executor_message.__class__, CommandMessageInterface):
            observation = self.execute_in_env(lm_executor_message)
            lm_executor_message.set_observation(observation)
        return lm_executor_message

    def _parse_response(self, response: str) -> Message:
        """
        Attempts to parse the raw model string into either AnswerMessage or CommandMessage.
        """
        try:
            return AnswerMessage(response)
        except:
            logger.debug("Not an AnswerMessage, trying CommandMessage.")
            try:
                return CommandMessage(response)
            except:
                logger.debug("Could not parse as CommandMessage.")
                raise Exception("Could not parse LM response as AnswerMessage or CommandMessage.")

    def call_lm(self) -> Message:
        """
        Calls the language model and ensures the response is in valid format.
        Retries up to MAX_RETRIES if the response is invalid.
        """
        model_input = self.prompt
        iterations = 0
        
        start_progress(f"Getting response from LM")
        try:
            iterations = 0  # Make sure this is defined
            while iterations < MAX_RETRIES:
                model_response: ModelResponse = query(
                    model=self.agent_config.lm_config.model,
                    message=model_input,
                    temperature=TEMPERATURE,
                    max_tokens=self.agent_config.lm_config.max_output_tokens,
                    stop_sequences=[STOP_TOKEN],
                    helm=self.agent_config.lm_config.use_helm
                )

                model_response = model_response.remove_hallucinations()
                lm_response = model_response + f"\n{STOP_TOKEN}"

                try:
                    return self._parse_response(lm_response)
                except Exception as e:
                    logger.warning(f"Retrying {iterations + 1}/{MAX_RETRIES} after parse error: {e}")
                    iterations += 1

            # If we've exhausted all retries
            raise Exception("call_lm error: Max retries reached without valid response.")

        except Exception as e:
            logger.error(f"Error in call_lm: {str(e)}")
            raise  # Re-raise the exception after logging it

        finally:
            stop_progress()

    def execute_in_env(self, executor_message: CommandMessage) -> Observation:
        """
        Executes the command in the environment using self.kali_env,
        captures the output, and returns an Observation.
        """
        command = executor_message.command
        try:
            stdout, stderr = self.kali_env.run_command(
                command, timeout=TIMEOUT_PER_COMMAND, workdir="/app/", logging=True
            )
            observation_text = stdout.strip() + stderr.strip()
            return Observation(observation_text)
        except Exception as e:
            logger.exception(f"Failed to execute command: {command}.\nException: {str(e)}")
            return Observation(str(e))

    def to_dict(self) -> dict:
        """
        Serializes the ExecutorAgent state to a dictionary.
        """
        return {
            "config": self.agent_config.lm_config.__dict__,
            "memory": self.memory,
            "initial_prompt": getattr(self, "initial_prompt", None),
            "prompt": getattr(self, "prompt", None),
            'agent_id': self.agent_id,
            "timestamp": getattr(self, "timestamp", None),
        }

    @classmethod
    def from_dict(cls, data: dict, **kwargs) -> "ExecutorAgent":
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
        agent._agent_id = data['agent_id']
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
    def load_from_file(cls, filepath: str, **kwargs) -> "ExecutorAgent":
        """
        Loads an agent state from a JSON file and reconstructs it.
        """
        import json

        with open(filepath, "r") as f:
            data = json.load(f)
        return cls.from_dict(data, **kwargs)