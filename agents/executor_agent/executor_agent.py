from dataclasses import dataclass, field
from typing import List, Optional, Union

from agents.base_agent import AgentConfig, BaseAgent
from agents.prompts import STOP_TOKEN
from messages.action_messages.answer_message import AnswerMessage
from messages.action_messages.command_message import CommandMessage
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

TIMEOUT_PER_COMMAND = 120
MAX_RETRIES = 3
RETRY_DELAY = 30


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

    
    async def run(self, messages: List[Message]) -> Message:
        if len(messages) > 1:
            raise Exception(f"Accepts at most a single message, got {len(messages)}.")
        if len(messages) == 0:        
            self.model.formulate_prompt()
        else:
            message = messages[0]
            self.model.formulate_prompt(message)

        executor_message = self.execute()
        self.model.update_memory(executor_message)

        return executor_message

    async def modify_memory_and_run(self, input: str) -> None:
        self.model.prompt = input
        self.model.clear_memory()

        result = await self.run([])
        return result

    """
    NEED TO CHANGE THIS
    """
    def execute(self) -> Message:
        lm_executor_message = self.call_lm()
        # If the model decides to output a command, we run it in the environment
        logger.info(f"LM Response:\n{lm_executor_message.message}")
        if issubclass(lm_executor_message.__class__, CommandMessageInterface):
            observation = self.execute_in_env(lm_executor_message)
            lm_executor_message.set_observation(observation)
            
        return lm_executor_message


    def call_lm(self) -> Union[AnswerMessage, CommandMessage]:
        """
        Calls the language model and ensures the response is in valid format.
        Retries up to MAX_RETRIES if the response is invalid.
        """
        iterations = 0
        
        start_progress(f"Getting response from LM")
        try:
            iterations = 0  # Make sure this is defined
            while iterations < MAX_RETRIES:
                model_response = self.model.run()
                model_response._message = self.model.remove_hallucinations(model_response._message)
                lm_response = model_response._message + f"\n{STOP_TOKEN}"

                try:
                    return self.model.parse_response(lm_response)
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


    """
    NEED TO CHANGE THIS
    """
    def execute_in_env(self, executor_message: CommandMessage) -> ExecutorAgentMessage:
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