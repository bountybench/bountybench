from messages.agent_messages.agent_message import AgentMessage


class PatchAgentMessage(AgentMessage):
    def __init__(
        self,
        agent_id: str,
        message: str,
        success: bool = False,
        patch_files_dir: str = None,
        prev: AgentMessage = None,
        attrs: dict = None,
    ) -> None:
        self._success = success
        self._patch_files_dir = patch_files_dir
        super().__init__(agent_id=agent_id, message=message, prev=prev, attrs=attrs)

    @property
    def success(self) -> bool:
        return self._success

    @property
    def patch_files_dir(self) -> str:
        return self._patch_files_dir
    
    def to_dict(self) -> dict:
        agent_dict = self.agent_dict()
        agent_dict.update({
            "success": self.success,
            "patch_files_dir": self.patch_files_dir
        })
        base_dict = super(AgentMessage, self).to_dict() 
        agent_dict.update(base_dict)
        return agent_dict
        
    @classmethod
    def from_dict(cls, data: dict) -> "PatchAgentMessage":
        agent_id = data.get("agent_id")
        message = data.get("message", "")
        success = data.get("success", False)
        patch_files_dir = data.get("patch_files_dir")
        attrs = {
            key: data[key]
            for key in data
            if key
            not in [
                "message_type",
                "agent_id",
                "message",
                "success",
                "patch_files_dir",
                "action_messages",
            ]
        }
        agent_message = cls(
            agent_id=agent_id,
            message=message,
            success=success,
            patch_files_dir=patch_files_dir,
            attrs=attrs,
        )

        for action_data in data.get("action_messages", []):
            from messages.message_utils import message_from_dict

            action_message = message_from_dict(action_data)
            agent_message.add_action_message(action_message)

        return agent_message
