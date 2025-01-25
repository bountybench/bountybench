from typing import List
from dataclasses import dataclass
from pathlib import Path

from agents.base_agent import AgentConfig, BaseAgent
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.webscraper_agent_message import WebscraperMessage
from messages.message import Message
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

@dataclass
class WebscraperAgentConfig(AgentConfig):
    website: str

    def to_dict(self):
        return {
            "website": self.website
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            website=data["website"]
        )

class WebscraperAgent(BaseAgent):

    def __init__(self, agent_id, agent_config: WebscraperAgentConfig):
        self.website = agent_config.website
        super().__init__(agent_id, agent_config)

    async def run(self, messages: List[AgentMessage]) -> AgentMessage:

        # TODO: Implement the agent logic here
        # Await the addition of a new URL to HUNTR / the queue
        prev_agent_message = messages[0]
        bounty_link = await self._get_new_url(self.website)
        return self._parse_url(bounty_link, prev_agent_message)
    
    async def _get_new_url(self, website) -> str:
        """
        TODO: Get the new URL from the message.

        Args:
            messages (List[AgentMessage])

        Returns:
            str: The new URL.
        """
        return "https://huntr.com/bounties/f1e0fdce-00d7-4261-a466-923062800b12"

    def _parse_url(self, bounty_link: str, prev_agent_message: AgentMessage) -> Message:
        """
        Parses the extraction url into a WebscraperMessage object.

        Args:
            bounty_link (str): The URL to be parsed.
            prev_agent_message (AgentMessage): The previous agent message.

        Returns:
            WebscraperMessage: The webscraper message.

        Raises:
            TypeError: If url is not a string.
            ExtractionParsingError: If required fields are missing or invalid.
        """
        if not isinstance(bounty_link, str):
            raise TypeError("URL must be a string.")

        return WebscraperMessage(
            agent_id=self.agent_id,
            message="New URL added to the queue",
            bounty_link=bounty_link,
            success=True,
            website=self.website,
            prev=prev_agent_message
        )