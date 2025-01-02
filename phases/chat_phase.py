from typing import Optional, Tuple, Any
from phases.base_phase import BasePhase
from responses.response import Response
from responses.answer_response import AnswerResponseInterface
from agents.chat_agent.chat_agent import ChatAgent
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class ChatPhase(BasePhase):
    """
    Phase that cycles through:
      - ChatAgent
    Checks for answer submission (Chat) to end early.
    """
    REQUIRED_AGENTS = [ChatAgent]

    async def run_one_iteration(
        self,
        agent_instance: Any,
        previous_output: Optional[Response],
        iteration_num: int
    ) -> Tuple[Response, bool]:
        """
        1) Call the agent with the previous_response as input (if any).
        2) If ChatAgent produces an AnswerResponseInterface, treat as answer submission -> finalize & done.
        4) Otherwise continue.
        """
        # Prepare input response list for agent
        input_list = []
        if previous_output is not None:
            input_list.append(previous_output)

        response = await agent_instance.run(input_list)

        # Check for answer submission (ExecutorAgent)
        if isinstance(response, AnswerResponseInterface):
            logger.info("Termination successful!")
            self._set_phase_summary("detect_success")
            return response, True
            
        # Otherwise, continue looping
        return response, False        