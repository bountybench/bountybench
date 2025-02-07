from messages.agent_messages.agent_message import AgentMessage
from typing import List

class WebscraperMessage(AgentMessage):
    def __init__(self, agent_id: str, message: str, website: str, bounty_links: List[str], last_bounty_link: str, prev: AgentMessage = None, success: bool = False) -> None:
        self._success = success
        self._bounty_links = bounty_links
        self._website = website
        self._last_bounty_link = last_bounty_link
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
    
    @property
    def last_bounty_link(self) -> str:
        return self._last_bounty_link

    def to_dict(self) -> dict:
        agent_dict = self.agent_dict()
        agent_dict.update({
            "success": self.success,
            "bounty_links": self.bounty_links,
            "website": self.website,
            "last_bounty_link": self.last_bounty_link
        })
        base_dict = super(AgentMessage, self).to_dict() 
        agent_dict.update(base_dict)
        return agent_dict