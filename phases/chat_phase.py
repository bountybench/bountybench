from typing import Any, Dict, List, Optional, Tuple, Type

from agents.base_agent import AgentConfig, BaseAgent
from agents.chat_agent.chat_agent import ChatAgent
from messages.action_messages.answer_message_interface import AnswerMessageInterface
from messages.message import Message
from messages.phase_messages.phase_message import PhaseMessage
from phases.base_phase import BasePhase
from resources.base_resource import BaseResource
from resources.default_resource import DefaultResource
from resources.model_resource.model_resource import ModelResourceConfig
from utils.logger import get_main_logger
from workflows.base_workflow import BaseWorkflow

logger = get_main_logger(__name__)


class ChatPhase(BasePhase):
    """
    ChatPhase is responsible for handling chat-based interactions in the workflow.
    """

    AGENT_CLASSES: List[Type[BaseAgent]] = [ChatAgent]

    def __init__(self, workflow: "BaseWorkflow", **kwargs):
        """
        Initialize the ChatPhase.

        Args:
            workflow (BaseWorkflow): The parent workflow.
            **kwargs: Additional keyword arguments.
        """
        self.model: str = kwargs.get("model", "")
        self.helm: Any = kwargs.get("helm")
        super().__init__(workflow, **kwargs)

    def define_agents(self) -> Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]:
        """
        Define the agents required for the ChatPhase.

        Returns:
            Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]: A dictionary mapping agent names to their types and configurations.
        """
        chat_config = AgentConfig()

        return {
            "chat_agent": (ChatAgent, chat_config),
        }
    
    def define_default_resources(self) -> Dict[str, Tuple[Type['BaseResource'], Any]]:
        """
        Define resource classes and their configurations required by the ChatPhase.

        Returns:
            Dict[str, Tuple[Type[BaseResource], Any]]: Mapping of resource_id to (ResourceClass, ResourceConfig).
        """
        return [
            (DefaultResource.MODEL, ModelResourceConfig.create(model=self.model))
        ]

    async def run_one_iteration(
        self,
        phase_message: PhaseMessage,
        agent_instance: Any,
        previous_output: Optional[Message],
    ) -> Message:
        """
        Run a single iteration of the ChatPhase.

        This method performs the following steps:
        1. Call the agent with the previous_message as input (if any).
        2. If ChatAgent produces an AnswerMessageInterface, treat as hallucination -> finalize & done.
        3. Otherwise continue.

        Args:
            phase_message (PhaseMessage): The current phase message.
            agent_instance (Any): The agent instance to run.
            previous_output (Optional[Message]): The output from the previous iteration.

        Returns:
            Message: The resulting message from the agent.
        """
        input_list: List[Message] = []
        if previous_output is not None:
            input_list.append(previous_output)

        message: Message = await agent_instance.run(input_list)

        if isinstance(agent_instance, ChatAgent):
            if isinstance(message, AnswerMessageInterface):
                logger.status("Chat agent produced an answer message!")
                phase_message.set_summary("completed_with_answer")
                phase_message.set_complete()

        return message
