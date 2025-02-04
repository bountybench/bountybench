from typing import List
from dataclasses import dataclass
from pathlib import Path
import os
from agents.base_agent import AgentConfig, BaseAgent
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.webscraper_agent_message import WebscraperMessage
from messages.message import Message
from utils.logger import get_main_logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import asyncio

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

    def get_known_urls(self) -> set:
        """Get set of URLs that have already been found."""
        file_path = os.path.join('agents/webscraper_agent', 'hackerone_report_urls.txt')
        if not os.path.exists(file_path):
            return set()
        
        with open(file_path, 'r') as f:
            return set(line.strip() for line in f if line.strip())

    def get_latest_report_url(self) -> str:
        """Get the URL of the most recent public HackerOne report."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        try:
            driver.get("https://hackerone.com/hacktivity?querystring=&filter=type:public&order_direction=DESC&order_field=latest_disclosable_activity_at")
            
            wait = WebDriverWait(driver, 10)
            first_report = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/reports/']"))
            )
            
            return first_report.get_attribute('href')
            
        finally:
            driver.quit()

    def save_url_to_file(self, url: str) -> None:
        """Save URL to hackerone_report_urls.txt file."""
        file_path = os.path.join('agents/webscraper_agent', 'hackerone_report_urls.txt')
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'a') as f:
            f.write(url + '\n')
        logger.info(f"Saved new URL to {os.path.abspath(file_path)}")

    def get_latest_huntr_url(self) -> str:
        """Get the URL of the most recent public Huntr report."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        try:
            driver.get("https://huntr.com/bounties/hacktivity")
            wait = WebDriverWait(driver, 10)
            bounty_links = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href^='/bounties/']"))
            )

            # Ensure the first valid bounty link is selected (ignoring "/bounties/disclose")
            for i, link in enumerate(bounty_links):
                report_url = link.get_attribute("href")
                if "/bounties/disclose" not in report_url:  # Exclude incorrect links
                    if not report_url.startswith("https://huntr.com"):
                        report_url = "https://huntr.com" + report_url
                    return report_url
            
        finally:
            driver.quit()

    async def _get_new_url(self, website) -> str:
        """Wait for and return a new report URL."""
        if website == "https://hackerone.com/reports/":
            known_urls = self.get_known_urls()
            logger.info(f"Currently tracking {len(known_urls)} known HackerOne reports")
            
            while True:
                try:
                    latest_url = self.get_latest_report_url()
                    if latest_url not in known_urls:
                        logger.info(f"Found new HackerOne report: {latest_url}")
                        self.save_url_to_file(latest_url)
                        return latest_url
                    
                    logger.info("No new HackerOne reports found. Checking again in 60 seconds...")
                    await asyncio.sleep(60)
                    
                except Exception as e:
                    logger.error(f"Error checking for new HackerOne reports: {e}")
                    logger.info("Retrying in 60 seconds...")
                    await asyncio.sleep(60)
        
        elif website == "https://huntr.com/bounties":
            known_urls = self.get_known_huntr_urls()
            logger.info(f"Currently tracking {len(known_urls)} known Huntr reports")
            
            while True:
                try:
                    latest_url = self.get_latest_huntr_url()
                    if latest_url not in known_urls:
                        logger.info(f"Found new Huntr report: {latest_url}")
                        self.save_huntr_url_to_file(latest_url)
                        return latest_url
                    
                    logger.info("No new Huntr reports found. Checking again in 60 seconds...")
                    await asyncio.sleep(60)
                    
                except Exception as e:
                    logger.error(f"Error checking for new Huntr reports: {e}")
                    logger.info("Retrying in 60 seconds...")
                    await asyncio.sleep(60)
        
        return "https://huntr.com/bounties/f1e0fdce-00d7-4261-a466-923062800b12"  # Default fallback

    def get_known_huntr_urls(self) -> set:
        """Get set of Huntr URLs that have already been found."""
        file_path = os.path.join('agents/webscraper_agent', 'huntr_report_urls.txt')
        if not os.path.exists(file_path):
            return set()
        
        with open(file_path, 'r') as f:
            return set(line.strip() for line in f if line.strip())

    def save_huntr_url_to_file(self, url: str) -> None:
        """Save URL to huntr_report_urls.txt file."""
        file_path = os.path.join('agents/webscraper_agent', 'huntr_report_urls.txt')
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'a') as f:
            f.write(url + '\n')
        logger.info(f"Saved new Huntr URL to {os.path.abspath(file_path)}")

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