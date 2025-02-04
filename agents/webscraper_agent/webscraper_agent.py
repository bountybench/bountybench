from typing import List
from dataclasses import dataclass
from pathlib import Path
import os
from agents.base_agent import AgentConfig, BaseAgent
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.webscraper_agent_message import WebscraperMessage
from messages.message import Message
from utils.logger import get_main_logger
import asyncio
from .website_handlers.webscraper_handler_factory import WebscraperHandlerFactory

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
        self.handler = WebscraperHandlerFactory.create_handler(self.website)
        super().__init__(agent_id, agent_config)

    async def _get_new_url(self, website) -> str:
        """Wait for and return a new report URL."""
        known_urls = self.handler.get_known_urls()
        logger.info(f"Currently tracking {len(known_urls)} known reports")

        while True:
            try:
                latest_url = self.handler.get_latest_report_url()
                if latest_url not in known_urls:
                    logger.info(f"Found new report: {latest_url}")
                    self.handler.save_url_to_file(latest_url)
                    return latest_url
                
                logger.info("No new reports found. Checking again in 60 seconds...")
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error checking for new reports: {e}")
                logger.info("Retrying in 60 seconds...")
                await asyncio.sleep(60)

    async def run(self, messages: List[AgentMessage]) -> AgentMessage:
        prev_agent_message = messages[0]
        bounty_link = await self._get_new_url(self.website)
        return self._parse_url(bounty_link, prev_agent_message)
    
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