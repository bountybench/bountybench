from messages.agent_messages.agent_message import AgentMessage

class PatchAgentMessage(AgentMessage):
    def __init__(self, agent_id: str, message: str, success: bool = False, patch_files_dir: str=None, prev: AgentMessage = None) -> None:
        self._success = success
        self._patch_files_dir = patch_files_dir
        super().__init__(agent_id, message, prev)
    
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