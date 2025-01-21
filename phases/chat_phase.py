from agents.base_agent import AgentConfig, BaseAgent
from agents.chat_agent.chat_agent import ChatAgent
from messages.phase_messages.phase_message import PhaseMessage
from phases.base_phase import BasePhase
from resources.base_resource import BaseResource
from resources.model_resource.model_resource import ModelResource, ModelResourceConfig
from messages.action_messages.answer_message_interface import AnswerMessageInterface
from messages.message import Message
from typing import Any, Dict, List, Optional, Tuple, Type
from utils.logger import get_main_logger
from workflows.base_workflow import BaseWorkflow


logger = get_main_logger(__name__)

class ChatPhase(BasePhase):
    AGENT_CLASSES = [ChatAgent]

    def __init__(self, workflow: 'BaseWorkflow', **kwargs):
        self.model = kwargs.get('model')
        self.helm = kwargs.get('helm')
        super().__init__(workflow, **kwargs)

    def define_agents(self) -> Dict[str, Tuple[Type[BaseAgent], Optional[AgentConfig]]]:
        # Create the executor_config
        chat_config = AgentConfig()

        return {"chat_agent": (ChatAgent, chat_config),
        }
    
    def define_resources(self) -> Dict[str, Tuple[Type['BaseResource'], Any]]:
        """
        Define resource classes and their configurations required by the ChatPhase.

        Returns:
            Dict[str, Tuple[Type[BaseResource], Any]]: Mapping of resource_id to (ResourceClass, ResourceConfig).
        """

        resource_configs = {
            "model": (
                ModelResource,
                ModelResourceConfig.create(model=self.model)
            ),
        }
        return resource_configs

    async def run_one_iteration(
        self,
        phase_message: PhaseMessage,
        agent_instance: Any,
        previous_output: Optional[Message]
    ) -> Message:
        """
        1) Call the agent with the previous_message as input (if any).
        2) If ChatAgent produces an AnswerMessageInterface, treat as hallucination -> finalize & done.
        4) Otherwise continue.
        """
        # Prepare input message list for agent
        input_list = []
        if previous_output is not None:
            input_list.append(previous_output)
        logger.info(f"Running {agent_instance.agent_id}")
        message = await agent_instance.run(input_list)
        logger.info(f"Got message {message}")

        # Determine which agent name was used in this iteration
        _, agent_instance = self._get_current_agent()

        # Check for hallucination (ChatAgent)
        if isinstance(agent_instance, ChatAgent):
            if isinstance(message, AnswerMessageInterface):
                logger.status("Executor agent hallucinated an answer!")
                phase_message.set_summary("completed_with_hallucination")
                phase_message.set_complete()
                return message

        return message
