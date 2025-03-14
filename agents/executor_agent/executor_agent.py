import asyncio
from typing import List, Optional

from agents.base_agent import BaseAgent
from messages.action_messages.action_message import ActionMessage
from messages.action_messages.command_message import CommandMessage
from messages.action_messages.command_message_interface import CommandMessageInterface
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.executor_agent_message import ExecutorAgentMessage
from messages.convert_message_utils import cast_action_to_command
from messages.message import Message
from resources.init_files_resource import InitFilesResource
from resources.kali_env_resource import KaliEnvResource
from resources.memory_resource import MemoryResource
from resources.model_resource.model_resource import ModelResource
from resources.setup_resource import SetupResource
from utils.logger import get_main_logger
from utils.progress_logger import start_progress, stop_progress

logger = get_main_logger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 30


class ExecutorAgent(BaseAgent):

    REQUIRED_RESOURCES = [
        (InitFilesResource, "init_files"),
        KaliEnvResource,
        (ModelResource, "model"),
        (MemoryResource, "executor_agent_memory"),
    ]
    OPTIONAL_RESOURCES = [
        (SetupResource, "repo_resource"),
        (SetupResource, "bounty_resource"),
    ]
    ACCESSIBLE_RESOURCES = [
        KaliEnvResource,
        (InitFilesResource, "init_files"),
        (SetupResource, "repo_resource"),
        (SetupResource, "bounty_resource"),
        (ModelResource, "model"),
        (MemoryResource, "executor_agent_memory"),
    ]

    async def run(self, messages: List[Message]) -> Message:
        if len(messages) > 1:
            raise Exception(f"Accepts at most a single message, got {len(messages)}.")
        if len(messages) == 0:
            prev_agent_message = None
        else:
            prev_agent_message = messages[0]
            while prev_agent_message.version_next:
                prev_agent_message = prev_agent_message.version_next

        agent_message = ExecutorAgentMessage(
            agent_id=self.agent_id, prev=prev_agent_message
        )

        await self.execute(agent_message, prev_agent_message)

        return agent_message

    async def execute(
        self,
        agent_message: ExecutorAgentMessage,
        prev_agent_message: Optional[AgentMessage] = None,
    ) -> Message:
        
        model_action_message = await self.call_lm(prev_agent_message)
        if not model_action_message:
            agent_message.set_message("Model failed to produce a valid response.")
            return agent_message

        agent_message.add_child_message(model_action_message)

        logger.info(f"LM Response:\n{model_action_message.message}")
        if issubclass(model_action_message.__class__, CommandMessageInterface):
            kali_action_message = self.execute_in_env(model_action_message)
            if not kali_action_message:
                return
            agent_message.add_child_message(kali_action_message)
            return kali_action_message

        return model_action_message

    async def call_lm(
        self, lm_input_message: Optional[Message] = None
    ) -> Optional[ActionMessage]:
        """
        Calls the language model and ensures the response is in valid format.
        Retries up to MAX_RETRIES if the response is invalid.
        Immediately fails on non-retryable errors like quota limits.
        """
        iterations = 0

        start_progress(f"Getting response from LM")
        try:
            iterations = 0
            while iterations < MAX_RETRIES:
                try:
                    lm_input_message = self.executor_agent_memory.get_memory(
                        lm_input_message
                    )

                    model_output: ActionMessage = await asyncio.to_thread(
                        self.model.run, input_message=lm_input_message
                    )
                    parsed_response = self.parse_response(model_output)
                    return parsed_response
                except Exception as e:
                    error_msg = str(e)
                    if "No quota" in error_msg or "InsufficientQuotaError" in error_msg:
                        raise Exception(
                            f"API quota exceeded. Please check your model quota/limits"
                        )

                    logger.warning(
                        f"Retrying {iterations + 1}/{MAX_RETRIES} after parse error: {e}"
                    )
                    iterations += 1

            # If we've exhausted all retries
            raise Exception(
                "call_lm error: Max retries reached without valid response."
            )

        except Exception as e:
            logger.error(f"Error in call_lm: {str(e)}")
            raise  # Re-raise the exception after logging it

        finally:
            stop_progress()

    def parse_response(self, action_message: ActionMessage) -> ActionMessage:
        """
        Attempts to parse the ActionMessage into a CommandMessage.
        """
        try:
            # Convert ActionMessage to CommandMessage
            command_message = cast_action_to_command(action_message)
            return command_message

        except Exception as e:
            logger.info(f"LM responded with: {action_message.message}")
            logger.debug(f"Could not parse response as CommandMessage. Error: {e}")
            action_message.set_message(
                f"Could not parse response as CommandMessage. Error: {e}"
            )
            return action_message

    def execute_in_env(self, executor_message: CommandMessage) -> ActionMessage:
        """
        Executes the command in the environment using self.kali_env,
        captures the output, and returns an ActionMessage.
        """
        try:
            kali_message = self.kali_env.run(executor_message)

            return kali_message

        except Exception as e:
            logger.exception(
                f"Failed to execute command: {executor_message.command}.\nException: {str(e)}"
            )
            return ActionMessage(
                resource_id=self.kali_env.resource_id,
                message=str(e),
                prev=executor_message,
            )

    def to_dict(self) -> dict:
        """
        Serializes the ExecutorAgent state to a dictionary.
        """
        return {
            "agent_id": self.agent_id,
            "timestamp": getattr(self, "timestamp", None),
        }
