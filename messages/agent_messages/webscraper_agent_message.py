from messages.agent_messages.agent_message import AgentMessage
from typing import List

class WebscraperMessage(AgentMessage):
    def __init__(self, agent_id: str, message: str, website: str, bounty_links: List[str], prev: AgentMessage = None, success: bool = False) -> None:
        if bounty_links is None:
            raise ValueError("bounty_links cannot be None")
        if not isinstance(bounty_links, list):
            raise ValueError("bounty_links must be a list")
            
        self._success = success
        self._bounty_links = bounty_links
        self._website = website
        super().__init__(agent_id, message, prev)

    @property
    def success(self) -> bool:
        return self._success
 
    @property
    def bounty_links(self) -> List[str]:
        return self._bounty_links
    
    @property
    def website(self) -> str:
        return self._website

    def to_dict(self) -> dict:
        agent_dict = self.agent_dict()
        agent_dict.update({
            "success": self.success,
            "bounty_links": self.bounty_links,
            "website": self.website
        })
        base_dict = super(AgentMessage, self).to_dict() 
        agent_dict.update(base_dict)
        return agent_dict