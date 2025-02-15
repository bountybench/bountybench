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


    def to_broadcast_dict(self) -> dict:
        base_dict = super(AgentMessage, self).to_broadcast_dict() 
        agent_dict = {
            "success": self.success,
            "patch_files_dir": self.patch_files_dir
        }
        agent_dict.update(base_dict)
        return agent_dict
    
    def to_log_dict(self) -> dict:
        base_dict = super(AgentMessage, self).to_log_dict() 
        agent_dict = {
            "success": self.success,
            "patch_files_dir": self.patch_files_dir
        }
        agent_dict.update(base_dict)
        return agent_dict