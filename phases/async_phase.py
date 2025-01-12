from typing import Any, Dict, Optional, Callable, Awaitable, Tuple
from datetime import datetime

from .base_phase import BasePhase
from messages.message import Message
from phase_messages.phase_message import PhaseMessage
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class AsyncPhase(BasePhase):
    """Async version of BasePhase that supports interactive mode"""

    async def run_phase_async(self, prev_phase_message: PhaseMessage) -> PhaseMessage:
        """
        Async version of run_phase that supports non-interactive mode
        """
        logger.debug(f"Entering run_phase_async for phase {self.name}")
        
        last_agent_message = prev_phase_message.agent_messages[-1] if prev_phase_message.agent_messages else None
        curr_phase_message = PhaseMessage(agent_messages=[])

        try:
            for iteration_num in range(1, self.phase_config.max_iterations + 1):
                if curr_phase_message.complete:
                    break

                agent_id, agent_instance = self._get_current_agent()
                logger.info(f"Running iteration {iteration_num} of {self.name} with {agent_id}")

                # Get and process the agent's message
                message = agent_instance.get_next_message(
                    phase_message=curr_phase_message,
                    previous_output=last_agent_message
                )
                
                result_message = agent_instance.process_message(message)
                curr_phase_message.agent_messages.append(result_message)

                logger.info(f"Finished iteration {iteration_num} of {self.name} with {agent_id}")
                if curr_phase_message.complete:
                    break

                last_agent_message = curr_phase_message.agent_messages[-1]
                self.iteration_count += 1
                self.current_agent_index += 1

            if not self.phase_summary:
                self._set_phase_summary("completed_failure")

            return curr_phase_message
            
        finally:
            self.deallocate_resources()

    async def run_interactive(
        self,
        prev_phase_message: PhaseMessage,
        request_user_input: Callable[[str, Dict], Awaitable[Dict]]
    ) -> PhaseMessage:
        """
        Execute the phase in interactive mode.
        """
        logger.debug(f"Entering run_interactive for phase {self.name}")

        last_agent_message = prev_phase_message.agent_messages[-1] if prev_phase_message.agent_messages else None
        curr_phase_message = PhaseMessage(agent_messages=[])

        try:
            for iteration_num in range(1, self.phase_config.max_iterations + 1):
                if curr_phase_message.complete:
                    break

                agent_id, agent_instance = self._get_current_agent()
                logger.info(f"Running iteration {iteration_num} of {self.name} with {agent_id}")

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
                curr_phase_message.agent_messages.append(result_message)

                logger.info(f"Finished iteration {iteration_num} of {self.name} with {agent_id}")
                if curr_phase_message.complete:
                    break

                last_agent_message = curr_phase_message.agent_messages[-1]
                self.iteration_count += 1
                self.current_agent_index += 1

            if not self.phase_summary:
                self._set_phase_summary("completed_failure")

            return curr_phase_message
            
        finally:
            self.deallocate_resources()
