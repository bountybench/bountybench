from enum import Enum

from messages.action_messages.action_message import ActionMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message
from messages.message_handler import MessageHandler
from messages.message_utils import message_dict
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


class IterationType(Enum):
    AGENT = "agent"
    PHASE = "phase"


class InteractiveController:
    def __init__(self, workflow):
        self.workflow = workflow
        self.workflow_message = workflow.workflow_message
        self.agent_manager = workflow.agent_manager
        self.resource_manager = workflow.resource_manager
        self._setup_message_handler()

    def _setup_message_handler(self):
        self.message_handler = MessageHandler(self.agent_manager, self.resource_manager)
        logger.debug("Setup message handler")

    def get_num_iteration(self, num_iter, type_iter) -> int:
        num_iteration = num_iter
        current_iteration = self.workflow.current_phase.get_current_iteration()
        max_iteration = self.workflow.current_phase.phase_config.max_iterations
        if type_iter == IterationType.PHASE:
            phase_iter_len = len(self.workflow.current_phase.agents)
            remaining_agent_iter = current_iteration % phase_iter_len
            if remaining_agent_iter > 0:
                num_iteration = remaining_agent_iter + (num_iter - 1) * phase_iter_len
            else:
                num_iteration = num_iter * phase_iter_len
        return min(num_iteration, max_iteration - current_iteration)

    async def get_last_message(self) -> str:
        if self.workflow.current_phase:
            result = self.workflow.current_phase.last_agent_message
            return result.message if result else ""
        return ""

    async def set_last_message(self, message_id: str):
        workflow_messages = message_dict.get(self.workflow_message.workflow_id, {})
        message = workflow_messages.get(message_id)
        if isinstance(message, ActionMessage):
            message = message.parent
        if (
            self.workflow.current_phase
            and message
            and isinstance(message, AgentMessage)
        ):
            await self.workflow.current_phase.set_last_agent_message(message)

    async def run_message(self, message_id: str):
        workflow_messages = message_dict.get(self.workflow_message.workflow_id, {})
        message = workflow_messages.get(message_id)
        if message.next or isinstance(message, ActionMessage):
            message = await self.message_handler.run_message(message)
            return message
        return None

    async def run_next_message(self):
        workflow_messages = message_dict.get(self.workflow_message.workflow_id, {})
        if len(workflow_messages) > 0:
            _, last_message = list(workflow_messages.items())[-1]
            if last_message.next:
                last_message = await self.message_handler.run_message(last_message)
                return last_message
            if last_message.parent and last_message.parent.next:
                last_message = await self.message_handler.run_message(
                    last_message.parent
                )
                return last_message
        return None

    async def edit_message(self, message_id: str, new_message_data: str) -> Message:
        workflow_messages = message_dict.get(self.workflow_message.workflow_id, {})
        message = workflow_messages.get(message_id)
        message = await self.message_handler.edit_message(message, new_message_data)
        return message

    async def edit_and_run_message(
        self, message_id: str, new_message_data: str
    ) -> Message:
        workflow_messages = message_dict.get(self.workflow_message.workflow_id, {})
        message = workflow_messages.get(message_id)
        message = await self.message_handler.edit_message(message, new_message_data)
        if message.next or isinstance(message, ActionMessage):
            message = await self.message_handler.run_message(message)
            return message
        return None

    async def change_current_model(self, new_model_name: str):
        self.workflow.params["model"] = new_model_name
        self.resource_manager.update_model(new_model_name)
        self.agent_manager.update_phase_agents_models(new_model_name)
        logger.info(f"Workflow model changed to {new_model_name}")

    async def set_mock_model(self, use_mock_model: bool):
        self.workflow.use_mock_model = use_mock_model
        self.resource_manager.update_mock_model(use_mock_model)
        self.agent_manager.update_phase_agents_mock_model(use_mock_model)

    async def set_interactive_mode(self, interactive: bool):
        if self.workflow.interactive != interactive:
            self.workflow.interactive = interactive
            logger.debug(f"Workflow interactive mode set to {interactive}")

            # Update the interactive mode for the current phase
            if self.workflow.current_phase:
                await self.workflow.current_phase.set_interactive_mode(interactive)

            # Update the interactive mode for all remaining phases
            for phase in self.workflow.phase_graph:
                if phase != self.workflow.current_phase:
                    phase.phase_config.interactive = interactive

            if not interactive:
                # If switching to non-interactive, trigger next iteration
                await self.workflow.next_iteration_queue.put(1)

    async def toggle_version(self, message_id: str, direction: str):
        workflow_messages = message_dict.get(self.workflow_message.workflow_id, {})
        message = workflow_messages.get(message_id)

        if not message:
            raise ValueError(f"Message with id {message_id} not found")

        if direction == "prev":
            target_message = message.version_prev
        elif direction == "next":
            target_message = message.version_next
        else:
            raise ValueError("Invalid direction. Must be 'prev' or 'next'")

        from messages.message_utils import generate_subtree

        subtree = generate_subtree(target_message)

        return subtree
