import asyncio
from dataclasses import dataclass
from typing import List, Optional

from agents.base_agent import AgentConfig, BaseAgent, IterationFailure
from messages.action_messages.action_message import ActionMessage
from messages.action_messages.command_message import CommandMessage
from messages.action_messages.command_message_interface import CommandMessageInterface
from messages.action_messages.error_action_message import ErrorActionMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.executor_agent_message import ExecutorAgentMessage
from messages.convert_message_utils import cast_action_to_command
from messages.message import Message
from resources.model_resource.model_resource import ModelResponseFailure
from resources.resource_type import ResourceType
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 30


@dataclass
class ExecutorAgentConfig(AgentConfig):
    """Configuration for ExecutorAgent"""


class ExecutorAgent(BaseAgent):

    REQUIRED_RESOURCES = [
        ResourceType.INIT_FILES,
        ResourceType.KALI_ENV,
        ResourceType.MODEL,
        ResourceType.MEMORY,
    ]
    OPTIONAL_RESOURCES = [
        ResourceType.REPO_SETUP,
        ResourceType.BOUNTY_SETUP,
    ]
    ACCESSIBLE_RESOURCES = [
        ResourceType.KALI_ENV,
        ResourceType.MODEL,
        ResourceType.MEMORY,
    ]

    def __init__(self, agent_id: str, agent_config: ExecutorAgentConfig):
        self.last_executor_agent_message = None
        super().__init__(agent_id, agent_config)

    async def run(self, messages: List[Message]) -> Message:
        if len(messages) > 1:
            raise Exception(f"Accepts at most a single message, got {len(messages)}.")
        if len(messages) == 0:
            prev_agent_message = None
        else:
            prev_agent_message = messages[0]
            while prev_agent_message.version_next:
                prev_agent_message = prev_agent_message.version_next

        self.last_executor_agent_message = ExecutorAgentMessage(
            agent_id=self.agent_id, prev=prev_agent_message
        )

        try:
            await self.execute(prev_agent_message)
        except Exception as e:
            agent_message_str = self.last_executor_agent_message.message or ""
            self.last_executor_agent_message.set_message(
                f"{agent_message_str}.\nExecutor agent iteration failed\n\n{str(e)}"
            )

            # Wrap and raise custom exception that carries the agent message
            raise IterationFailure(
                message=f"agent.execute failed: {str(e)}",
                agent_message=self.last_executor_agent_message,
            ) from e

        return self.last_executor_agent_message

    async def execute(
        self,
        prev_agent_message: Optional[AgentMessage] = None,
    ) -> None:
        model_action_message = await self.call_lm(prev_agent_message)
        if not model_action_message:
            self.last_executor_agent_message.set_message(
                "Model failed to produce a valid response."
            )
            return

        self.last_executor_agent_message.add_child_message(model_action_message)

        logger.info(f"LM Response:\n{model_action_message.message}")
        if issubclass(model_action_message.__class__, CommandMessageInterface):
            # Note: can adjust the check condition later
            if "finalsubmissioncommand" in model_action_message.command.lower():
                # Note: create an empty action message to protect the memory resource
                empty_action_message = ActionMessage(
                    resource_id="submission",
                    message="",
                    prev=model_action_message,
                )
                self.last_executor_agent_message.add_child_message(empty_action_message)
                self.last_executor_agent_message.set_submission(value=True)
                return

            kali_action_message = self.execute_in_env(model_action_message)
            if not kali_action_message:
                self.last_executor_agent_message.set_message(
                    "Kali failed to produce a valid response."
                )
                return
            self.last_executor_agent_message.add_child_message(kali_action_message)
        else:
            self.last_executor_agent_message.set_message(
                "Model did not return a valid command. Kali Linux action skipped."
            )

    async def call_lm(
        self, lm_input_message: Optional[Message] = None
    ) -> Optional[ActionMessage]:
        """
        Calls the language model and ensures the response is in valid format.
        Retries up to MAX_RETRIES if the response is invalid.
        Immediately fails on non-retryable errors like quota limits.
        If parsing fails after MAX_RETRIES, returns the last raw response.
        Uses a 5-minute timeout for the LLM call.
        """
        iterations = 0

        last_raw_response = None  # Store the last raw response in case parsing fails
        error_history = []  # Track error history across retries
        command_reminder_added = False

        try:
            lm_input_message = self.resources.executor_agent_memory.get_memory(
                lm_input_message
            )
            while iterations < MAX_RETRIES:
                try:
                    logger.info(f"Getting response from LM")
                    model_output: ActionMessage = await asyncio.to_thread(
                        self.resources.model.run,
                        input_message=lm_input_message,
                    )

                    last_raw_response = model_output
                except asyncio.TimeoutError as e:
                    error_entry = {
                        "type": "TimeoutError",
                        "message": f"LLM call timed out: {str(e)}",
                        "attempt": iterations + 1,
                    }
                    error_history.append(error_entry)

                    logger.warning(
                        f"LLM call timed out: {str(e)}. Retrying {iterations + 1}/{MAX_RETRIES}"
                    )
                    iterations += 1
                    continue
                except Exception as e:
                    error_msg = str(e)
                    exception_type = type(e).__name__

                    error_entry = {
                        "type": exception_type,
                        "message": error_msg,
                        "attempt": iterations + 1,
                    }

                    # Check for status code on the exception)
                    if hasattr(e, "status_code"):
                        status_code = e.status_code
                        error_entry["status_code"] = status_code
                    elif isinstance(e, ModelResponseFailure) and hasattr(
                        e.exception, "status_code"
                    ):
                        status_code = e.exception.status_code
                        error_entry["status_code"] = status_code

                    if (
                        isinstance(e, ModelResponseFailure)
                        and "invalid prompt" in error_msg.lower()
                    ):
                        # Log associated input with invalid prompt failures
                        error_entry["input"] = e.input

                    # Also don't retry quota errors
                    if "No quota" in error_msg or "InsufficientQuotaError" in error_msg:
                        error_history.append(error_entry)
                        raise Exception(
                            f"API quota exceeded. Please check your model quota/limits"
                        )

                    error_history.append(error_entry)
                    logger.warning(
                        f"Retrying {iterations + 1}/{MAX_RETRIES} after model query error: {e}"
                    )
                    iterations += 1
                    continue  # Skip to next iteration without trying to parse

                try:
                    logger.info(f"Parsing response from LM")
                    parsed_response = self.parse_response(model_output)
                    if error_history:
                        parsed_response.add_to_additional_metadata(
                            "error_history", error_history
                        )
                    return parsed_response
                except Exception as e:
                    exception_type = type(e).__name__
                    error_msg = str(e)

                    error_entry = {
                        "type": exception_type,
                        "message": error_msg,
                        "attempt": iterations + 1,
                    }
                    error_history.append(error_entry)

                    logger.warning(
                        f"Retrying {iterations + 1}/{MAX_RETRIES} after parse error: {e}"
                    )
                    iterations += 1

                    if not command_reminder_added and lm_input_message:
                        # Add the reminder to use Command: format
                        lm_input_message.memory = lm_input_message.memory or ""
                        lm_input_message.memory += (
                            '\n\nMake sure to include "Command:" in your response.'
                        )
                        command_reminder_added = True

            # If we've exhausted all retries but have a raw response, return it
            if last_raw_response:
                if error_history:
                    last_raw_response.add_to_additional_metadata(
                        "error_history", error_history
                    )
                return last_raw_response

            # If we've exhausted all retries
            raise Exception(
                "call_lm error: Max retries reached without valid response."
            )

        except Exception as e:
            exception_type = type(e).__name__
            error_msg = str(e)

            logger.error(f"Error in call_lm: {error_msg}")
            model_failure_message = ErrorActionMessage(
                resource_id=self.resources.model.resource_id,
                message=error_msg,
                error_type=exception_type,
                error_history=error_history,  # Include the full error history
            )
            self.last_executor_agent_message.add_child_message(model_failure_message)

            raise

    def parse_response(self, action_message: ActionMessage) -> ActionMessage:
        """
        Attempts to parse the ActionMessage into a CommandMessage.
        """
        try:
            # Convert ActionMessage to CommandMessage
            command_message = cast_action_to_command(action_message)
            return command_message

        except Exception as e:
            logger.warning(f"Could not parse response as CommandMessage. Error: {e}")
            raise

    def execute_in_env(self, executor_message: CommandMessage) -> ActionMessage:
        """
        Executes the command in the environment using self.resources.kali_env,
        captures the output, and returns an ActionMessage.
        """
        try:
            kali_message = self.resources.kali_env.run(executor_message)
            return kali_message

        except Exception as e:
            exception_type = type(e).__name__
            logger.exception(
                f"Failed to execute command: {executor_message.command}.\nException: {str(e)}"
            )
            kali_failure_message = ErrorActionMessage(
                resource_id=self.resources.kali_env.resource_id,
                message=str(e),
                error_type=exception_type,
                prev=executor_message,
            )
            self.last_executor_agent_message.add_child_message(kali_failure_message)
            raise

    def to_dict(self) -> dict:
        """
        Serializes the ExecutorAgent state to a dictionary.
        """
        return {
            "agent_id": self.agent_id,
            "timestamp": getattr(self, "timestamp", None),
        }
