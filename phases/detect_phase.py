from typing import Optional, Tuple, Any
from phases.base_phase import BasePhase
from messages.message import Message
from messages.answer_message import AnswerMessageInterface
from agents.executor_agent.executor_agent import ExecutorAgent
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class DetectPhase(BasePhase):
    """
    Phase that cycles through:
      - ExecutorAgent
    Checks for answer submission (Executor) to end early.
    """
    REQUIRED_AGENTS = [ExecutorAgent]

    def run_one_iteration(
        self,
        agent_instance: Any,
        previous_output: Optional[Message]
    ) -> Tuple[Message, bool]:
        """
        1) Call the agent with the previous_message as input (if any).
        2) If ExecutorAgent produces an AnswerMessageInterface, treat as answer submission -> finalize & done.
        4) Otherwise continue.
        """
        # Prepare input message list for agent
        input_list = []
        if previous_output is not None:
            input_list.append(previous_output)

        message = agent_instance.run(input_list)

        # Check for answer submission (ExecutorAgent)
        if isinstance(message, AnswerMessageInterface):
            logger.info("Detect successful!")
            self._set_phase_summary("detect_success")
            return message, True
            
        # Otherwise, continue looping
        return message, False        