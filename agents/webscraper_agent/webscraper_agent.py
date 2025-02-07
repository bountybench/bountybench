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

    async def _get_new_urls(self, website, last_bounty_link) -> str:
        """Wait for and return a new report URL."""
        known_urls = self.handler.get_known_urls()
        logger.info(f"Currently tracking {len(known_urls)} known reports")

        while True:
            try:
                # Get the latest report URLs in the order from newest to oldest
                latest_urls = self.handler.get_latest_report_urls()
                new_urls = []

                # Filter out known URLs and save new ones
                for url in latest_urls:
                    if url == last_bounty_link:
                        break
                    if url not in known_urls:
                        new_urls.append(url)
                        logger.info(f"Found new report: {url}")
                
                if new_urls:
                    return new_urls
                else:
                    logger.info("No new reports found. Checking again in 60 seconds...")
                    await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error checking for new reports: {e}")
                logger.info("Retrying in 60 seconds...")
                await asyncio.sleep(60)

    async def run(self, messages: List[AgentMessage]) -> WebscraperMessage:
        # Get the previous agent message
        prev_agent_message = messages[0]
        last_bounty_link = prev_agent_message.last_bounty_link

        # Get the new bounty links
        new_bounty_links = await self._get_new_urls(self.website, last_bounty_link)
        self.last_bounty_link = new_bounty_links[0]

        # Save the new bounty links
        self.handler.save_urls_to_file(new_bounty_links)

        # Parse the new bounty links
        return self._parse_urls(new_bounty_links, prev_agent_message)
    
    def _parse_urls(self, bounty_links: List[str], prev_agent_message: AgentMessage) -> WebscraperMessage:
        """
        Parses the extraction urls into a WebscraperMessage object.

        Args:
            bounty_link (str): The URL to be parsed.
            prev_agent_message (AgentMessage): The previous agent message.

        Returns:
            WebscraperMessage: The webscraper message.

        Raises:
            TypeError: If url is not a string.
            ExtractionParsingError: If required fields are missing or invalid.
        """

        return WebscraperMessage(
            agent_id=self.agent_id,
            message="New URL added to the queue",
            bounty_links=bounty_links,
            last_bounty_link=bounty_links[0],
            success=True,
            website=self.website,
            prev=prev_agent_message
        )