import asyncio
from dataclasses import dataclass
from typing import List

from agents.base_agent import AgentConfig, BaseAgent
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.webscraper_agent_message import WebscraperMessage
from utils.logger import get_main_logger

from .website_handlers.webscraper_handler_factory import WebscraperHandlerFactory

logger = get_main_logger(__name__)


@dataclass
class WebscraperAgentConfig(AgentConfig):
    website: str = "https://huntr.com/bounties"

    def __post_init__(self):
        """Validate config after initialization"""
        if not self.website.startswith(
            ("https://huntr.com/bounties", "https://hackerone.com/reports/")
        ):
            raise ValueError(
                "Unsupported website. Must be either Huntr or HackerOne URL."
            )

    def to_dict(self) -> dict:
        return {"website": self.website}

    @classmethod
    def from_dict(cls, data: dict):
        website = data.get("website", "https://huntr.com/bounties")
        return cls(website=website)


class WebscraperAgent(BaseAgent):
    def __init__(self, agent_id: str, agent_config: WebscraperAgentConfig) -> None:
        self.website = agent_config.website
        self.handler = WebscraperHandlerFactory.create_handler(self.website)
        super().__init__(agent_id, agent_config)

    async def _get_new_urls(self, last_bounty_link: str) -> List[str]:
        """
        Wait for and return new report URLs.

        Args:
            last_bounty_link: The most recently processed bounty URL

        Returns:
            List of new bounty URLs found
        """
        known_urls = self.handler.get_known_urls()
        logger.info(f"Currently tracking {len(known_urls)} known reports")

        while True:
            try:
                latest_urls = self.handler.get_latest_report_urls()
                new_urls = []

                # Use a set to remove duplicates while preserving order
                seen = set()
                for url in latest_urls:
                    if url == last_bounty_link:
                        break
                    if url not in known_urls and url not in seen:
                        new_urls.append(url)
                        seen.add(url)

                if new_urls:
                    return new_urls

                await asyncio.sleep(60)

            except Exception as e:
                await asyncio.sleep(60)

    async def run(self, messages: List[AgentMessage]) -> WebscraperMessage:
        """
        Process messages and find new bounty URLs.

        Args:
            messages: List of input messages

        Returns:
            WebscraperMessage containing any new bounty URLs found
        """
        prev_agent_message = messages[0]
        last_bounty_link = None

        if prev_agent_message and prev_agent_message.bounty_links:
            last_bounty_link = prev_agent_message.bounty_links[0]
            logger.info(f"Last bounty link: {last_bounty_link}")
        else:
            logger.info("No previous bounty links found.")

        new_bounty_links = await self._get_new_urls(last_bounty_link)
        self.handler.save_urls_to_file(new_bounty_links)
        return self._parse_urls(new_bounty_links, prev_agent_message)

    def _parse_urls(
        self, bounty_links: List[str], prev_agent_message: AgentMessage
    ) -> WebscraperMessage:
        """
        Create WebscraperMessage from bounty URLs.

        Args:
            bounty_links: List of bounty URLs to include in message
            prev_agent_message: Previous message in the chain

        Returns:
            WebscraperMessage containing the bounty URLs
        """
        return WebscraperMessage(
            agent_id=self.agent_id,
            message="New URLs added to the queue",
            bounty_links=bounty_links,
            website=self.website,
            prev=prev_agent_message,
        )
