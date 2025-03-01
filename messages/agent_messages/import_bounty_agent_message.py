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
    
    def to_broadcast_dict(self) -> dict:
        base_dict = super().to_broadcast_dict()
        base_dict.update(
            {
                "success": self.success,
                "bounty_dirs": self.bounty_dirs,
                "bounty_links": self.bounty_links,
            }
        )
        return base_dict
    
    def to_log_dict(self) -> dict:
        base_dict = super().to_log_dict()
        base_dict.update(
            {
                "success": self.success,
                "bounty_dirs": self.bounty_dirs,
                "bounty_links": self.bounty_links,
            }
        )
        return base_dict
