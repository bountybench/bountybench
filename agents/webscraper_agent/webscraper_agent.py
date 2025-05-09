import asyncio
from dataclasses import dataclass
from typing import List

from agents.base_agent import AgentConfig, BaseAgent
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.import_bounty_agent_message import ImportBountyMessage
from messages.agent_messages.webscraper_agent_message import WebscraperMessage
from utils.logger import get_main_logger

from .website_handlers.webscraper_handler_factory import WebscraperHandlerFactory

logger = get_main_logger(__name__)


@dataclass
class WebscraperAgentConfig(AgentConfig):
    website: str = "https://huntr.com/bounties"
    bounty_dir: str = "agents/import_bounty_agent/bounties"
    max_bounties_to_scrape: int = 5

    def __post_init__(self):
        """Validate config after initialization"""
        if not self.website.startswith(
            ("https://huntr.com/bounties", "https://hackerone.com/reports/")
        ):
            raise ValueError(
                "Unsupported website. Must be either Huntr or HackerOne URL."
            )

    def to_dict(self) -> dict:
        return {
            "website": self.website,
            "bounty_dir": self.bounty_dir,
            "max_bounties_to_scrape": self.max_bounties_to_scrape,
        }

    @classmethod
    def from_dict(cls, data: dict):
        website = data.get("website", "https://huntr.com/bounties")
        bounty_dir = data.get("bounty_dir", "agents/import_bounty_agent/bounties")
        max_bounties_to_scrape = data.get("max_bounties_to_scrape", 5)
        return cls(
            website=website,
            bounty_dir=bounty_dir,
            max_bounties_to_scrape=max_bounties_to_scrape,
        )


class WebscraperAgent(BaseAgent):
    def __init__(self, agent_id: str, agent_config: WebscraperAgentConfig) -> None:
        self.website = agent_config.website
        self.bounty_dir = agent_config.bounty_dir
        self.handler = WebscraperHandlerFactory.create_handler(self.website)
        self.max_bounties_to_scrape = agent_config.max_bounties_to_scrape
        super().__init__(agent_id, agent_config)

    async def _get_new_urls(self, last_bounty_link: str) -> List[str]:
        """
        Wait for and return new report URLs.

        Args:
            last_bounty_link: The most recently processed bounty URL

        Returns:
            List of new bounty URLs found
        """
        known_urls = self.handler.get_known_urls(self.bounty_dir)
        logger.info(f"Currently tracking {len(known_urls)} known reports")
        logger.info(f"Looking for up to{self.max_bounties_to_scrape} new reports...")

        # Use a set to remove duplicates while preserving order
        seen = set()

        # Track consecutive failures
        consecutive_failures = 0
        max_consecutive_failures = 60

        while True:
            try:
                latest_urls = self.handler.get_latest_report_urls()
                logger.info(f"Found {len(latest_urls)} reports")
                new_urls = []

                for url in latest_urls:
                    if url == last_bounty_link:
                        logger.info(f"Reached last bounty link: {url}")
                    if url not in known_urls and url not in seen:
                        logger.info(f"Adding new bounty: {url}")
                        new_urls.append(url)
                        seen.add(url)
                    if len(new_urls) >= self.max_bounties_to_scrape:
                        logger.info(
                            f"Reached max bounties to scrape: {self.max_bounties_to_scrape}"
                        )
                        break

                if new_urls:
                    logger.info(f"Found {len(new_urls)} new reports.")
                    return new_urls

                consecutive_failures = 0

            except ConnectionError as ce:
                logger.warning(f"Network issue while fetching URLs: {ce}")
                consecutive_failures += 1
            except Exception as e:
                logger.error(f"Unexpected error in _get_new_urls: {e}")
                consecutive_failures += 1

            if consecutive_failures >= max_consecutive_failures:
                logger.error("Failed to fetch URLs for 60 consecutive attempts")
                raise

            await asyncio.sleep(60)

    async def run(self, messages: List[AgentMessage]) -> WebscraperMessage:
        """
        Process messages and find new bounty URLs.

        Args:
            messages: List of input messages

        Returns:
            WebscraperMessage containing any new bounty URLs found
        """
        prev_agent_message = messages[0] if messages else None
        last_bounty_link = None

        # If the previous message is an ImportBountyMessage, use the bounty_links
        if isinstance(prev_agent_message, ImportBountyMessage):
            if prev_agent_message.bounty_links:
                last_bounty_link = prev_agent_message.bounty_links[0]
                logger.info(f"Last bounty link: {last_bounty_link}")
        else:
            logger.info("No previous bounty links found.")

        new_bounty_links = await self._get_new_urls(last_bounty_link)
        self.handler.save_urls_to_file(new_bounty_links, self.bounty_dir)
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
