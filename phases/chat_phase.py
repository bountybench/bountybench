from typing import Dict, Optional, Tuple, Any, Type
from agents.base_agent import AgentConfig, BaseAgent
from agents.dataclasses.agent_lm_spec import AgentLMConfig
from messages.answer_message import AnswerMessageInterface
from messages.message import Message
from phases.base_phase import BasePhase, PhaseMessage
from resources.base_resource import BaseResource
from agents.chat_agent.chat_agent import ChatAgent, ChatAgentConfig
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
        # assume we get model through some kwargs situation with the Message
        lm_config = AgentLMConfig.create(model=self.model, use_helm=self.helm)
        # Create the chat_config
        chat_config = ChatAgentConfig(
            lm_config=lm_config,
        )
        return {"chat_agent": (ChatAgent, chat_config),
        }
    
    def define_resources(self) -> Dict[str, Tuple[Type['BaseResource'], Any]]:
        return {}

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

        message = await agent_instance.run(input_list)
        phase_message.add_agent_message(message)

        # Determine which agent name was used in this iteration
        _, agent_instance = self._get_current_agent()

        # Check for hallucination (ChatAgent)
        if isinstance(agent_instance, ChatAgent):
            if isinstance(message, AnswerMessageInterface):
                logger.status("Executor agent hallucinated an answer!")
                self._set_phase_summary("completed_with_hallucination")
                phase_message.set_complete()
                return message

        return message
