from typing import List
from dataclasses import dataclass
from pathlib import Path

from agents.base_agent import AgentConfig, BaseAgent
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.webscraper_agent_message import ScraperMessage
from messages.message import Message
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

@dataclass
class WebscraperAgentConfig(AgentConfig):
    webscraper_files_dir: str
    bounty_link: str

    def to_dict(self):
        return {
            "webscraper_files_dir": self.webscraper_files_dir,
            "bounty_link": self.bounty_link
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            webscraper_files_dir=data["webscraper_files_dir"],
            bounty_link=data["bounty_link"],
        )

class WebscraperAgent(BaseAgent):

    def __init__(self, agent_id, agent_config: WebscraperAgentConfig):

        self.webscraper_files_dir = Path(agent_config.webscraper_files_dir)
        self.bounty_link = Path(agent_config.bounty_link)

        super().__init__(agent_id, agent_config)

    async def run(self, messages: List[AgentMessage]) -> AgentMessage:

        # TODO: Implement the agent logic here
        # Await the addition of a new URL to HUNTR / the queue
        prev_agent_message = messages[0]
        return self._parse_url(prev_agent_message)

    def _parse_url(self, prev_agent_message: AgentMessage) -> Message:
        """
        Parses the extraction url into an ScraperMessage object.

        Args:
            prev_agent_message (AgentMessage)

        Returns:
            ScraperMessage: The scraper message.

        Raises:
            TypeError: If url is not a string.
            ExtractionParsingError: If required fields are missing or invalid.
        """
        if not isinstance(self.bounty_link, str):
            raise TypeError("URL must be a string.")

        return ScraperMessage(
            agent_id=self.agent_id,
            message="New URL added to the queue",
            bounty_link=self.bounty_link,
            success=True,
            webscraper_files_dir=self.webscraper_files_dir,
            prev=prev_agent_message
        )