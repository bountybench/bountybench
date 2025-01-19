from agents.agent_manager import AgentManager
from resources.resource_manager import ResourceManager

from messages.message import Message
from messages.action_messages.action_message import ActionMessage
from messages.agent_messages.agent_message import AgentMessage

class RerunManager:
    def __init__(self, agent_manager: AgentManager, resource_manager: ResourceManager):
        self.agent_manager = agent_manager
        self.resource_manager = resource_manager

    async def run_edited(self, edited_message: Message) -> Message:
        if edited_message.next:
            if isinstance(edited_message, ActionMessage):
                message = await self._rerun_action_message(edited_message.next, edited_message)
                return message
            elif isinstance(edited_message, AgentMessage):
                message = await self._rerun_agent_message(edited_message.next, edited_message)
                return message
            else:
                raise ValueError("Unsupported message type for rerun")
        else:
            raise ValueError("No defined next actions to run, please continue to next iteration")
        
    async def rerun(self, message: Message) -> Message:
        if isinstance(message, ActionMessage):
            message = await self._rerun_action_message(message, message.prev)
            return message
        elif isinstance(message, AgentMessage):
            message = await self._rerun_agent_message(message, message.prev)
            return message
        else:
            raise ValueError("Unsupported message type for rerun")

    async def _rerun_action_message(self, old_message: Message, input_message: Message) -> Message:
        resource = self.resource_manager.get_resource(old_message.resource_id)
        new_message = resource.run(input_message)
        self._update_version_links(old_message, new_message)
        return new_message

    async def _rerun_agent_message(self, old_message: Message, input_message: Message) -> Message:
        agent = self.agent_manager.get_agent(old_message.agent_id)
        new_message = await agent.run(input_message)
        self._update_version_links(old_message, new_message)
        return new_message

    def _update_version_links(self, old_message: Message, new_message: Message) -> Message:
        new_message.set_next(old_message.next)
        old_message.set_version_next(new_message)
        new_message.set_version_prev(old_message)