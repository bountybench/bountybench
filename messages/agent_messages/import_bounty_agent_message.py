from typing import Any, Dict, List
from messages.agent_messages.agent_message import AgentMessage

class ImportBountyMessage(AgentMessage):
    def __init__(
        self,
        agent_id: str,
        message: str,
        success: str,
        bounty_dirs: List[str],
        bounty_links: List[str],
        prev: AgentMessage = None,
    ) -> None:
        self._success = success
        self._bounty_links = bounty_links
        self._bounty_dirs = bounty_dirs
        super().__init__(agent_id, message, prev)

    @property
    def success(self) -> bool:
        return self._success
    
    @property
    def bounty_dirs(self) -> List[str]:
        return self._bounty_dirs
    
    @property
    def bounty_links(self) -> List[str]:
        return self._bounty_links
    
    def to_dict(self) -> Dict[str, Any]:
        agent_dict = self.agent_dict()
        agent_dict.update({
            "success": self.success,
            "bounty_dirs": self._bounty_dirs,
            "bounty_links": self._bounty_links,
        })
        base_dict = super(AgentMessage, self).to_dict() 
        agent_dict.update(base_dict)
        return agent_dict