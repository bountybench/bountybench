from messages.agent_messages.agent_message import AgentMessage
from typing import Union

class ScraperMessage(AgentMessage):
    def __init__(self, agent_id: str, message: str, webscraper_files_dir: Union[str, None], bounty_link: str, prev: AgentMessage = None, success: bool = False) -> None:
        self.success = success
        self._bounty_link = bounty_link
        self._webscraper_files_dir = webscraper_files_dir
        super().__init__(agent_id, message, prev)

    @property
    def success(self) -> bool:
        return self._success
 
    @property
    def bounty_link(self) -> str:
        return self._bounty_link
    
    @property
    def webscraper_files_dir(self) -> str:
        return self._webscraper_files_dir

    def to_dict(self) -> dict:
        agent_dict = self.agent_dict()
        agent_dict.update({
            "success": self.success,
            "bounty_link": self.bounty_link,
            "webscraper_files_dir": self.webscraper_files_dir
        })
        base_dict = super(AgentMessage, self).to_dict() 
        agent_dict.update(base_dict)
        return agent_dict