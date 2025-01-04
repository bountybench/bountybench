from dataclasses import dataclass
from typing import List, Optional

from agents.base_agent import AgentConfig, BaseAgent
from agents.dataclasses.agent_lm_spec import AgentLMConfig
from agents.executor_agent.prompt import INITIAL_PROMPT, STOP_TOKEN
from agents.utils import truncate_input_to_max_tokens
from models.model_response import ModelResponse
from models.query import query
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.resource_manager import ResourceManager
from resources.setup_resource import SetupResource
from responses.answer_response import AnswerResponse
from responses.command_response import CommandResponse
from responses.command_response_interface import CommandResponseInterface
from responses.observation import Observation
from responses.response import Response
from utils.logger import get_main_logger
from utils.workflow_logger import WorkflowLogger

logger = get_main_logger(__name__)

TIMEOUT_PER_COMMAND = 120
MAX_RETRIES = 3
RETRY_DELAY = 30
TEMPERATURE = 0.5

@dataclass
class ExecutorAgentConfig(AgentConfig):
    id: str
    lm_config: AgentLMConfig
    target_host: str
    initial_prompt: Optional[str]=None


class ExecutorAgent(BaseAgent):
    memory: List[str] = []

    # Switch from listing just resource classes to (ResourceClass, "attr_name").
    # BaseAgent will do: self.init_files = resource_manager.get_resource("init_files")
    # etc.
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
    CONFIG_CLASS = ExecutorAgentConfig
    def __init__(self, agent_config: ExecutorAgentConfig):#, resource_manager: ResourceManager):
        """
        Args:
            agent_config: ExecutorAgentConfig containing model, initial prompt, and target host.
            resource_manager: ResourceManager instance responsible for managing resources.
        """
        # Pass the agent_config and resource_manager to BaseAgent
        super().__init__(agent_config)#, resource_manager)

        # Initialize specific attributes
        if hasattr(agent_config, "initial_prompt"):
            self.initial_prompt = agent_config.initial_prompt
        self.prompt = self.initial_prompt

        # If a target_host is provided, run health_check on self.kali_env
        self.target_host = agent_config.target_host

        if self.target_host: 
            self.kali_env.health_check(self.target_host)
        

    
    #def register_resources(self, resource_manager: ResourceManager) -> None:
        #super().register_resources(resource_manager)
        #if self.target_host: 
            #self.kali_env.health_check(self.target_host)
        

    


    def run(self, responses: List[Response]) -> Response:
        if len(responses) > 1:
            raise Exception(f"Accepts at most a single response, got {len(responses)}.")

        if len(responses) == 0:        
            self.formulate_prompt()
        else:
            response = responses[0]
            self.formulate_prompt(response)

        executor_response = self.execute()
        self._update_memory(executor_response)

        return executor_response

    def _update_memory(self, response: Response) -> None:
        if len(self.memory) >= self.agent_config.lm_config.max_iterations_stored_in_memory:
            self.memory = self.memory[1:] + [response.response]
        else:
            self.memory.append(response.response)

    def formulate_prompt(self, response: Optional[Response] = None) -> str:
        """
        Formulates the prompt, including the truncated memory.
        """
        if response:
            if self.initial_prompt:
                self._update_memory(response)
            else:
                self.initial_prompt = response.response
        

        truncated_input = truncate_input_to_max_tokens(
            max_input_tokens=self.agent_config.lm_config.max_input_tokens,
            model_input="\n".join(self.memory),
            model=self.agent_config.lm_config.model,
            use_helm=self.agent_config.lm_config.use_helm,
        )
        prompt = self.initial_prompt + truncated_input
        self.prompt = prompt
        return prompt

    def execute(self) -> Response:
        lm_executor_response = self.call_lm()
        # If the model decides to output a command, we run it in the environment
        if issubclass(lm_executor_response.__class__, CommandResponseInterface):
            observation = self.execute_in_env(lm_executor_response)
            lm_executor_response.set_observation(observation)
        logger.info(f"LM Response:\n{lm_executor_response.response}")
        return lm_executor_response

    def _parse_response(self, response: str) -> Response:
        """
        Attempts to parse the raw model string into either AnswerResponse or CommandResponse.
        """
        try:
            return AnswerResponse(response)
        except:
            logger.debug("Not an AnswerResponse, trying CommandResponse.")
            try:
                return CommandResponse(response)
            except:
                logger.debug("Could not parse as CommandResponse.")
                raise Exception("Could not parse LM response as AnswerResponse or CommandResponse.")

    def call_lm(self) -> Response:
        """
        Calls the language model and ensures the response is in valid format.
        Retries up to MAX_RETRIES if the response is invalid.
        """
        model_input = self.prompt
        iterations = 0
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
                logger.warning(f"Retrying {iterations}/{MAX_RETRIES} after parse error: {e}")
                iterations += 1

        raise Exception("call_lm error: Max retries reached without valid response.")

    def execute_in_env(self, executor_response: CommandResponse) -> Observation:
        """
        Executes the command in the environment using self.kali_env,
        captures the output, and returns an Observation.
        """
        command = executor_response.command
        try:
            stdout, stderr = self.kali_env.run_command(
                command, timeout=TIMEOUT_PER_COMMAND, workdir="/app/", logging=True
            )
            observation_text = stdout.strip() + stderr.strip()
            logger.info(f"Command in environment: {command}\nstdout: {stdout.strip()}\nstderr: {stderr.strip()}")
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