from typing import Optional, Tuple, Any
from phases.base_phase import BasePhase
from responses.response import Response
from responses.answer_response import AnswerResponseInterface
from agents.executor_agent.executor_agent import ExecutorAgent
from agents.patch_agent.patch_agent import PatchAgent
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class PatchPhase(BasePhase):
    """
    Phase that cycles through:
      - ExecutorAgent
      - PatchAgent
    Checks for hallucination (Executor) or patch success (Patch) to end early.
    """
    REQUIRED_AGENTS = [ExecutorAgent, PatchAgent]

    async def run_one_iteration(
        self,
        agent_instance: Any,
        previous_output: Optional[Response],
        iteration_num: int
    ) -> Tuple[Response, bool]:
        """
        1) Call the agent with previous_output as input.
        2) If ExecutorAgent produces an AnswerResponseInterface -> hallucination -> finalize & done.
        3) If PatchAgent produces an AnswerResponseInterface -> patch success -> finalize & done.
        4) Otherwise continue.
        """
        input_list = []
        if previous_output is not None:
            input_list.append(previous_output)

        response = agent_instance.run(input_list)

        # Determine which agent name was used in this iteration
        agent_name, _ = self._get_agent()

        if agent_name == "ExecutorAgent":
            if isinstance(response, AnswerResponseInterface):
                logger.info("Executor agent hallucinated an answer!")
                self._set_phase_summary("completed_with_hallucination")
                return response, True

        elif agent_name == "PatchAgent":
            if isinstance(response, AnswerResponseInterface):
                logger.info("Patch Success!")
                self._set_phase_summary("patch_success")
                return response, True

        return response, False
