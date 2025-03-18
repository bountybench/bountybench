import inspect
from typing import Optional

from agents.agent_manager import AgentManager
from messages.action_messages.action_message import ActionMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message
from messages.phase_messages.phase_message import PhaseMessage
from resources.resource_manager import ResourceManager
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


class MessageHandler:
    def __init__(self, agent_manager: AgentManager, resource_manager: ResourceManager):
        self.agent_manager = agent_manager
        self.resource_manager = resource_manager

    async def run_message(self, message: Message) -> Message:
        """Regenerates next message if a .next exists"""
        if message.next:
            if isinstance(message, ActionMessage):
                message = await self._run_action_message(message.next, message)
                return message
            elif isinstance(message, AgentMessage):
                message = await self._run_agent_message(message.next, message)
                return message
            else:
                raise ValueError("Unsupported message type for run")
        else:
            raise ValueError(
                "No defined next actions to run, please continue to next iteration"
            )

    async def _run_action_message(
        self, old_message: ActionMessage, input_message: Message
    ) -> Message:
        # Ensure we start with the "latest version" of old_message
        while old_message.version_next:
            old_message = old_message.version_next

        # Also grab the final version of the parent, if it has one
        parent_message = old_message.parent
        while parent_message and parent_message.version_next:
            parent_message = parent_message.version_next

        # Run the resource again
        resource = self.resource_manager.get_resource(old_message.resource_id)
        new_action: ActionMessage = resource.run(input_message)

        # Keep next link if the old action had one
        if old_message.next:
            new_action.set_next(old_message.next)

        # If parent is an AgentMessage, just attach new_action to it
        if parent_message and isinstance(parent_message, AgentMessage):
            parent_message.add_child_message(new_action)

        # Always update version links with set_version=False like in old version
        self.update_version_links(
            old_message=old_message,
            new_message=new_action,
            set_version=False,
            parent_message=parent_message,
        )
        return new_action

    async def _run_agent_message(
        self, old_message: Message, input_message: Message
    ) -> Message:
        agent = self.agent_manager.get_agent(old_message.agent_id)
        logger.info(f"running agent message with agent {agent}")
        new_message = await agent.run([input_message])
        logger.info(f"message output: {new_message.message}")
        self.update_version_links(old_message, new_message, set_version=False)
        return new_message

    def _clone_message(
        self,
        old_message: Message,
        edit: Optional[str] = None,
        prev: Optional[Message] = None,
    ) -> Message:
        if not old_message:
            raise ValueError("Trying to clone None Messasge")
        dic = old_message.__dict__
        cls = type(old_message)
        init_method = cls.__init__
        signature = inspect.signature(init_method)
        params = {}
        for name, param in signature.parameters.items():
            if "_" + name in dic:
                params[name] = dic["_" + name]

        params["prev"] = prev
        params["message"] = edit if edit else params["message"]
        new_message = cls(**params)

        if isinstance(new_message, AgentMessage) and old_message.iteration != None:
            new_message.set_iteration(old_message.iteration)

        return new_message

    def _clone_parent_agent_message(
        self, old_message: ActionMessage, parent_message: AgentMessage, edit: str
    ) -> Message:
        new_parent_message = self._clone_message(parent_message)
        logger.info(f"new_parent_message prev: {parent_message.prev}")
        new_parent_message.set_prev(parent_message.prev)
        self.update_version_links(parent_message, new_parent_message)
        logger.info(f"new_parent_message next: {parent_message.next}")

        new_prev_action = self._clone_action_chain(
            parent_message.current_children, old_message, new_parent_message
        )
        new_message = self._clone_message(old_message, edit=edit, prev=new_prev_action)

        # Maintain the next link so workflow can handle the run message
        if old_message.next:
            new_message.set_next(old_message.next)
        logger.info(
            f"new_parent_message current children: {new_parent_message.current_children}"
        )
        self.update_version_links(
            old_message,
            new_message,
            set_version=False,
            parent_message=new_parent_message,
        )

        logger.info(
            f"Parent AgentMessage edited, ID: {old_message.id} to ID: {new_message.id}"
        )
        logger.info(f"new_message: {new_message}")
        return new_message

    def _clone_action_chain(
        self,
        actions_list: list[ActionMessage],
        old_message: ActionMessage,
        new_parent: AgentMessage,
    ) -> Message:
        if not actions_list:
            return None

        prev_action = actions_list[0]
        if prev_action == old_message:
            return None

        new_prev_action = self._clone_message(prev_action)
        self.update_version_links(
            prev_action, new_prev_action, set_version=False, parent_message=new_parent
        )

        while prev_action.next and prev_action.next != old_message:
            new_action = self._clone_message(prev_action.next, prev=new_prev_action)
            self.update_version_links(
                prev_action.next,
                new_action,
                set_version=False,
                parent_message=new_parent,
            )
            prev_action = prev_action.next
            new_prev_action = new_prev_action.next

        return new_prev_action

    async def edit_message(self, old_message: Message, edit: str) -> Message:
        while old_message.version_next:
            old_message = old_message.version_next

        logger.info(f"Latest version before edit: {old_message.id}")

        if not isinstance(old_message, ActionMessage):
            return self._finalize_edit(old_message, edit)

        parent_message = old_message.parent
        if parent_message and isinstance(parent_message, AgentMessage):
            return self._clone_parent_agent_message(old_message, parent_message, edit)
        else:
            return self._finalize_edit(old_message, edit)

    def _finalize_edit(self, old_message: Message, edit: str) -> Message:
        new_message = self._clone_message(old_message, edit=edit)
        new_message.set_prev(old_message.prev)
        self.update_version_links(old_message, new_message)

        logger.info(
            f"{old_message.__class__.__name__} message edited, ID: {old_message.id} to ID: {new_message.id}"
        )

        return new_message

    def update_version_links(
        self,
        old_message: Message,
        new_message: Message,
        set_version=True,
        parent_message=None,
    ) -> Message:
        if set_version:
            parent_message = old_message.parent
            new_message.set_version_prev(old_message)
        logger.info(
            f"old_message: {old_message.message}, ID: {old_message.id} with prev {old_message.prev} and next: {old_message.next}"
        )
        if (
            not new_message.parent
            or old_message.parent
            or new_message.parent == old_message.parent
        ):
            new_message.set_next(old_message.next)

        if isinstance(new_message, AgentMessage) and old_message.iteration != None:
            new_message.set_iteration(old_message.iteration)

        if not parent_message:
            parent_message = old_message.parent
        if parent_message:
            parent_message.add_child_message(new_message)
            if isinstance(parent_message, AgentMessage):
                # 1) find the top-level Phase
                phase = self.find_phase_parent(parent_message)
                # 2) broadcast from the Phase
                if phase:
                    from messages.message_utils import broadcast_update

                    broadcast_update(phase)

    def find_phase_parent(self, message: Message) -> Optional[PhaseMessage]:
        current = message
        while current.parent:
            if isinstance(current.parent, PhaseMessage):
                return current.parent
            current = current.parent
        return None
