import inspect
from typing import Optional

from agents.agent_manager import AgentManager
from messages.action_messages.action_message import ActionMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.message import Message
from messages.message_utils import broadcast_update
from messages.phase_messages.phase_message import PhaseMessage
from resources.resource_manager import ResourceManager


class RerunManager:
    def __init__(self, agent_manager: AgentManager, resource_manager: ResourceManager):
        self.agent_manager = agent_manager
        self.resource_manager = resource_manager

    async def run_from(self, message: Message) -> Message:
        if message.next:
            if isinstance(message, ActionMessage):
                message = await self._rerun_action_message(message.next, message)
                return message
            elif isinstance(message, AgentMessage):
                message = await self._rerun_agent_message(message.next, message)
                return message
            else:
                raise ValueError("Unsupported message type for rerun")
        else:
            raise ValueError(
                "No defined next actions to run, please continue to next iteration"
            )

    async def _rerun_action_message(
        self, old_message: Message, input_message: Message
    ) -> Message:
        resource = self.resource_manager.get_resource(old_message.resource_id)
        new_message = resource.run(input_message)
        self.update_version_links(old_message, new_message)
        return new_message

    async def _rerun_agent_message(
        self, old_message: Message, input_message: Message
    ) -> Message:
        agent = self.agent_manager.get_agent(old_message.agent_id)
        new_message = await agent.run([input_message])
        self.update_version_links(old_message, new_message)
        return new_message

    async def edit_message(self, old_message: Message, edit: str) -> Message:
        while old_message.version_next:
            old_message = old_message.version_next

        print(f"Latest version before edit: {old_message.id}")

        dic = old_message.__dict__
        cls = type(old_message)
        init_method = cls.__init__
        signature = inspect.signature(init_method)
        params = {}
        for name, param in signature.parameters.items():
            if "_" + name in dic:
                params[name] = dic["_" + name]

        params["prev"] = None
        params["message"] = edit
        new_message = cls(**params)

        new_message.set_prev(old_message.prev)
        self.update_version_links(old_message, new_message)

        print(f"New message created: {new_message.id}")
        print(
            f"Old message parent: {old_message.parent.id if old_message.parent else 'None'}"
        )
        print(
            f"New message parent: {new_message.parent.id if new_message.parent else 'None'}"
        )

        return new_message

    def update_version_links(
        self, old_message: Message, new_message: Message
    ) -> Message:
        new_message.set_version_prev(old_message)
        new_message.set_next(old_message.next)
        parent_message = old_message.parent
        if parent_message:
            if isinstance(parent_message, AgentMessage):
                parent_message.add_action_message(new_message)
                # 1) find the top-level Phase
                phase = self.find_phase_parent(parent_message)
                # 2) broadcast from the Phase
                if phase:
                    from messages.message_utils import broadcast_update

                    broadcast_update(phase)

            if isinstance(parent_message, PhaseMessage):
                parent_message.add_agent_message(new_message)

    def find_phase_parent(self, message: Message) -> Optional[PhaseMessage]:
        current = message
        while current.parent:
            if isinstance(current.parent, PhaseMessage):
                return current.parent
            current = current.parent
        return None
