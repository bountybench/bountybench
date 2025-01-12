from typing import Any, Dict, Optional, Callable, Awaitable, Tuple
from contextlib import asynccontextmanager
from datetime import datetime

from .base_phase import BasePhase
from messages.message import Message
from phase_messages.phase_message import PhaseMessage
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class AsyncPhase(BasePhase):
    """Async version of BasePhase that supports interactive mode"""

    async def run_interactive(
        self,
        prev_phase_message: PhaseMessage,
        request_user_input: Callable[[str, Dict], Awaitable[Dict]]
    ) -> PhaseMessage:
        """
        Execute the phase in interactive mode.

        Args:
            prev_phase_message (PhaseMessage): The message from the previous phase
            request_user_input (Callable): Function to request input from the user

        Returns:
            PhaseMessage: The message of the current phase
        """
        logger.debug(f"Entering run_interactive for phase {self.phase_config.phase_idx} ({self.phase_config.phase_name})")

        last_agent_message = prev_phase_message.agent_messages[-1]
        curr_phase_message = PhaseMessage(agent_messages=[])

        async with self._phase_context() as phase_ctx:
            for iteration_num in range(1, self.phase_config.max_iterations + 1):
                if curr_phase_message.complete:
                    break

                agent_id, agent_instance = self._get_current_agent()
                logger.info(f"Running iteration {iteration_num} of {self.name} with {agent_id}")

                async with phase_ctx.iteration(iteration_num, agent_id, last_agent_message) as iteration_ctx:
                    # Get the agent's next message
                    message = agent_instance.get_next_message(
                        phase_message=curr_phase_message,
                        previous_output=last_agent_message
                    )

                    # Request user input/modification
                    user_response = await request_user_input(agent_id, {
                        "original_message": message.to_dict(),
                        "context": {
                            "phase_name": self.name,
                            "iteration": iteration_num,
                            "agent": agent_id
                        }
                    })

                    # Create new message from user response
                    modified_message = Message.from_dict(user_response.get("message", message.to_dict()))
                    
                    # Process the modified message
                    result_message = agent_instance.process_message(modified_message)
                    iteration_ctx.set_output(result_message)
                    curr_phase_message.agent_messages.append(result_message)

                logger.info(f"Finished iteration {iteration_num} of {self.name} with {agent_id}")
                if curr_phase_message.complete:
                    break

                last_agent_message = curr_phase_message.agent_messages[-1]
                self.iteration_count += 1
                self.current_agent_index += 1

        if not self.phase_summary:
            self._set_phase_summary("completed_failure")

        self.deallocate_resources()
        return curr_phase_message

    @asynccontextmanager
    async def _phase_context(self):
        """Async context manager for phase execution"""
        try:
            yield self
        finally:
            pass  # Add any cleanup code here if needed

    @asynccontextmanager
    async def _iteration_context(self, iteration_num: int, agent_id: str, input_message: Message):
        """Async context manager for iteration execution"""
        try:
            yield self
        finally:
            pass  # Add any cleanup code here if needed
