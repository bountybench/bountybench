import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from agents.base_agent import AgentConfig, BaseAgent
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.import_bounty_agent_message import ImportBountyMessage
from utils.logger import get_main_logger
from .website_handlers.handler_factory import get_handler

logger = get_main_logger(__name__)

@dataclass
class ImportBountyAgentConfig(AgentConfig):
    """Configuration for the ImportBountyAgent"""
    bounty_dir: str

    def to_dict(self):
        """Convert config to dictionary format"""
        return {
            "bounties_dir": self.bounty_dir,
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create config from dictionary"""
        return cls(
            bounty_dir=data["bounty_dir"],
        )

class ImportBountyAgent(BaseAgent):
    """
    ImportBountyAgent is responsible for parsing out bounty metadata from a bounty report.
    
    This agent takes in a url to a bounty report, downloads the report, parses
    the relevant metadata and verifies its success.
    """

    def __init__(self, agent_id: str, agent_config: ImportBountyAgentConfig):
        """Initialize the agent with an ID and config"""
        self.bounty_dir = Path(agent_config.bounty_dir)
        super().__init__(agent_id, agent_config)

    def run(self, messages: List[AgentMessage]) -> AgentMessage:
        """
        Main execution method for the agent.
        
        Args:
            messages: List containing a single message with bounty URL and website
            
        Returns:
            ImportBountyMessage containing extracted metadata
            
        Raises:
            ValueError: If more than one message is received
            Exception: If any step fails
        """
        # Validate input message
        if len(messages) != 1:
            raise ValueError(f"Accepts only a single message, but received {len(messages)}.")

        prev_message = messages[0]
        bounty_link = prev_message._bounty_link
        website = prev_message._website

        try:
            # Download webpage and extract metadata
            report_dir = self._download_webpage(bounty_link, website)
            writeup = self._read_writeup(report_dir)
            metadata = self._extract_metadata(bounty_link, writeup, website)
            
            # Parse and save metadata
            import_bounty_message = self._parse_metadata_extraction(metadata)
            self._write_bounty_metadata(report_dir, import_bounty_message)

            return import_bounty_message

        except Exception as e:
            logger.error(f"Exception during bounty report handling: {e}")
            raise

    def _download_webpage(self, bounty_link: str, website: str) -> str:
        """
        Downloads the webpage from the bounty link using Selenium.
        
        Args:
            bounty_link: URL of the bounty report
            website: Base website URL (e.g. hackerone.com)
            
        Returns:
            Path to directory containing downloaded report
            
        Raises:
            Exception: If download or save fails
        """
        # Extract IDs from URL
        bounty_id = bounty_link.split("/")[-1]
        website_domain = website.split(".")[0].split("//")[-1]

        # Set up output paths
        OUTPUT_FOLDER = f"{self.bounty_dir}/{website_domain}_reports/"
        FAILED_LINKS_FILE = f"reports/{website_domain}_reports/failed_links.txt"

        # Configure headless Chrome
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu") 
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        try:
            # Load and render page
            driver.get(bounty_link)
            handler = get_handler(website, driver)
            if handler:
                handler.wait_for_page_load()
                handler.scroll_to_load_content()
            
            # Save rendered HTML
            page_html = driver.page_source
            report_dir = f'{OUTPUT_FOLDER}report_{bounty_id}'
            os.makedirs(report_dir, exist_ok=True)

            html_file_path = os.path.join(report_dir, f'report_{bounty_id}.html')
            with open(html_file_path, 'w', encoding='utf-8') as f:
                f.write(page_html)
            
            logger.info(f"Saved HTML: {html_file_path}")

        except Exception as e:
            # Log failed downloads
            logger.error(f"An error occurred while processing {bounty_link}: {e}")
            os.makedirs(os.path.dirname(FAILED_LINKS_FILE), exist_ok=True)
            with open(FAILED_LINKS_FILE, "a", encoding="utf-8") as f:
                f.write(f"{bounty_link}\n")
            raise
        finally:
            driver.quit()
            
        return report_dir
    
    def _setup_bounty_folder(self, output_dir: str) -> str:
        """TODO: Run create_bounty.sh script to create folder. Task dir name?"""
        return NotImplemented
    
    def _read_writeup(self, report_dir: str) -> str:
        """
        Read the downloaded HTML writeup file.
        
        Args:
            report_dir: Path to report directory
            
        Returns:
            HTML content as string, or empty string if file not found
        """
        bounty_id = report_dir.split("/")[-1]
        html_file_path = os.path.join(report_dir, f'{bounty_id}.html')
        try:
            with open(html_file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Writeup not found at: {html_file_path}")
            return ""
    
    def _write_bounty_metadata(self, report_dir: str, import_bounty_message: ImportBountyMessage):
        """
        Write extracted metadata to JSON file.
        
        Args:
            report_dir: Path to report directory
            import_bounty_message: Message containing metadata
            
        Raises:
            SystemExit: If metadata file cannot be written
        """
        metadata_path = os.path.join(report_dir, "bounty_metadata.json")
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
        
        with open(metadata_path, "w") as f:
            json.dump(import_bounty_message.to_dict(), f)

        if not os.path.exists(metadata_path):
            logger.error("Bounty metadata file not found")
            sys.exit(1)

    def _extract_metadata(self, bounty_link: str, writeup: str, website: str) -> dict[str, str]:
        """
        Extract metadata using appropriate website handler.
        
        Args:
            bounty_link: Original bounty URL
            writeup: HTML content of bounty report
            website: Base website URL
            
        Returns:
            Dictionary of extracted metadata fields
            
        Raises:
            ValueError: If no handler exists for website
        """
        handler = get_handler(website, None, writeup)
        if not handler:
            raise ValueError(f"No handler available for {website}")
        
        metadata = handler.extract_metadata()
        metadata['bounty_link'] = bounty_link  # Ensure we use the original link
        return metadata

    def _parse_metadata_extraction(self, metadata: Dict[str, str]) -> ImportBountyMessage:
        """
        Parse metadata dictionary into ImportBountyMessage.

        Args:
            metadata: Dictionary of extracted metadata fields

        Returns:
            ImportBountyMessage containing parsed metadata

        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ['bounty_link', 'CWE', 'CVE', 'severity', 
                         'disclosure_bounty', 'patch_bounty', 'vulnerable_commit']
        missing_fields = [field for field in required_fields if field not in metadata]
        if missing_fields:
            raise ValueError(f"Metadata is missing required fields: {', '.join(missing_fields)}")
        
        return ImportBountyMessage(
            agent_id=self.agent_id,
            message="Bounty metadata imported",
            success=True,
            bounty_link=metadata['bounty_link'],
            cwe=metadata['CWE'],
            cve=metadata['CVE'],
            severity=metadata['severity'], 
            disclosure_bounty=metadata['disclosure_bounty'],
            patch_bounty=metadata['patch_bounty'],
            vulnerable_commit=metadata['vulnerable_commit']
        )