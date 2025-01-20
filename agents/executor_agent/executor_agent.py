from dataclasses import dataclass, field
from typing import List, Optional, Union

from agents.base_agent import AgentConfig, BaseAgent
from messages.action_messages.action_message import ActionMessage
from messages.action_messages.answer_message import AnswerMessage
from messages.action_messages.command_message import CommandMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.executor_agent_message import ExecutorAgentMessage
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.model_resource.model_resource import ModelResource
from resources.setup_resource import SetupResource
from messages.action_messages.command_message_interface import CommandMessageInterface
from messages.message import Message
from utils.logger import get_main_logger
from utils.progress_logger import start_progress, stop_progress

logger = get_main_logger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 30

@dataclass
class ExecutorAgentConfig(AgentConfig):
    initial_prompt: Optional[str] = field(default=None)


class ExecutorAgent(BaseAgent):

    REQUIRED_RESOURCES = [
       (InitFilesResource, "init_files"),
        (KaliEnvResource, "kali_env"),
        (ModelResource, "model")

    ]
    OPTIONAL_RESOURCES = [(SetupResource, "repo_resource"), (SetupResource, "bounty_resource")]
    ACCESSIBLE_RESOURCES = [
        (KaliEnvResource, "kali_env"),
       (InitFilesResource, "init_files"),
        (SetupResource, "repo_resource"),
        (SetupResource, "bounty_resource"),
        (ModelResource, "model")]    
    

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


    async def run(self, messages: List[Message]) -> Message:
        if len(messages) > 1:
            raise Exception(f"Accepts at most a single message, got {len(messages)}.")
        if len(messages) == 0:        
            prev_agent_message = None
        else:
            prev_agent_message = messages[0]

        agent_message = ExecutorAgentMessage(agent_id=self.agent_id, prev=prev_agent_message, input_str=self.prompt)
        
        executor_message = self.execute(agent_message, prev_agent_message)
        self.model.update_memory(executor_message)
        self.prompt = executor_message.message

        return agent_message

    def execute(self, agent_message: ExecutorAgentMessage, prev_agent_message: Optional[AgentMessage] = None) -> Message:
        model_action_message = self.call_lm(prev_agent_message)
        if not model_action_message:
            return

        agent_message.add_action_message(model_action_message)

        # If the model decides to output a command, we run it in the environment
        logger.info(f"LM Response:\n{model_action_message.message}")
        if issubclass(model_action_message.__class__, CommandMessageInterface):
            kali_action_message = self.execute_in_env(model_action_message)
            if not kali_action_message:
                return
            self.model.update_memory(kali_action_message.message)
            agent_message.add_action_message(kali_action_message)
            return kali_action_message
        return model_action_message

    def call_lm(self, lm_input_message: Optional[Message] = None) -> CommandMessage:
        """
        Calls the language model and ensures the response is in valid format.
        Retries up to MAX_RETRIES if the response is invalid.
        """
        iterations = 0
        
        start_progress(f"Getting response from LM")
        try:
            iterations = 0 
            while iterations < MAX_RETRIES:
                try:
                    model_response = self.model.run(lm_input_message)
                    return model_response
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

    def execute_in_env(self, executor_message: CommandMessage) -> ActionMessage:
        """
        Executes the command in the environment using self.kali_env,
        captures the output, and returns an ActionMessage.
        """
        try:
            kali_message = self.kali_env.run(executor_message)
            return kali_message
        except Exception as e:
            logger.exception(f"Failed to execute command: {executor_message.command}.\nException: {str(e)}")
            return ActionMessage(resource_id=self.kali_env.resource_id, message=str(e), prev=executor_message)
        
    def to_dict(self) -> dict:
        """
        Serializes the ExecutorAgent state to a dictionary.
        """
        return {
            'agent_id': self.agent_id,
            "timestamp": getattr(self, "timestamp", None)
        }