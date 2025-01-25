from bs4 import BeautifulSoup
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import requests
from urllib.parse import urljoin

from agents.base_agent import AgentConfig, BaseAgent
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.import_bounty_agent_message import ImportBountyMessage
from messages.message import Message
import os
import json
import sys
from utils.logger import get_main_logger
import re

logger = get_main_logger(__name__)

@dataclass
class ImportBountyAgentConfig(AgentConfig):
    bounty_dir: str

    def to_dict(self):
        return {
            "bounties_dir": self.bounty_dir,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            bounty_dir=data["bounty_dir"],
        )

class ImportBountyAgent(BaseAgent):

    """
    ImportBountyAgent is responsible for parsing out bounty metadata from a bounty report.
    
    This agent takes in a url to a bounty report, downloads the report, parses
    the relevant metadata and verifies its success.
    """

    def __init__(self, agent_id, agent_config):
        self.bounty_dir = Path(agent_config.bounty_dir)
        super().__init__(agent_id, agent_config)

    async def run(self, messages: List[AgentMessage]) -> AgentMessage:
        # Get URL from message
        if len(messages) != 1:
            raise Exception(f"Accepts only a single message, but received {len(messages)}.")

        # Get bounty link and corresponding website from the webscraper agent message
        prev_agent_message = messages[0]
        bounty_link = prev_agent_message._bounty_link
        website = prev_agent_message._website

        try:
            # Download complete webpage from URL with Selenium in the report dir
            report_dir = await self._download_webpage(bounty_link, website)

            # Extract metadata info and write a bounty metadata file in the report dir
            writeup = self._read_writeup(report_dir)
            metadata = self._extract_metadata(bounty_link, writeup)
            import_bounty_message = self._parse_metadata_extraction(metadata)
            self._write_bounty_metadata(report_dir, import_bounty_message)

            return import_bounty_message
        except Exception as e:
            logger.error(f"Exception during bounty report handling: {e}")
            raise e

    async def _download_webpage(self, bounty_link: str, website: str) -> str:
        """
        Downloads the webpage from the bounty link using Selenium and saves it in the reports directory.
        """
        # Extract the bounty ID from the URL (e.g., 2819666 from https://hackerone.com/reports/2819666)
        bounty_id = bounty_link.split("/")[-1]

        # Extract the website domain (i.e. hackerone or huntr)
        website_domain = website.split(".")[0].split("//")[-1]

        OUTPUT_FOLDER = f"{self.bounty_dir}/{website_domain}_reports/"  # Folder where reports will be saved
        FAILED_LINKS_FILE = f"reports/{website_domain}_reports/failed_links.txt"  # File to store failed links

        # Set up Selenium with headless Chrome
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        # Initialize the Chrome driver
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        try:
            # Navigate to the URL
            driver.get(bounty_link)

            # Wait for either of the elements that indicate the page is fully loaded
            if website == "https://huntr.com/bounties":
                WebDriverWait(driver, 100).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//iframe[@owner='archetype' and @title='archetype' and contains(@style, 'display')]")
                    )
                )
            elif website == "https://hackerone.com/reports":
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.timeline-item.activity.spec-activity")
                    )
                )
            
            # Capture the entire HTML of the fully rendered page
            page_html = driver.page_source
            
            report_dir = f'{OUTPUT_FOLDER}report_{bounty_id}'
            os.makedirs(report_dir, exist_ok=True)

            # Save the page HTML
            html_file_path = os.path.join(report_dir, f'report_{bounty_id}.html')
            with open(html_file_path, 'w', encoding='utf-8') as f:
                f.write(page_html)
            
            logger.info(f"Saved HTML: {html_file_path}")

        except Exception as e:
            logger.error(f"An error occurred while processing {bounty_link}: {e}")
            with open(FAILED_LINKS_FILE, "a", encoding="utf-8") as f:
                f.write(f"{bounty_link}\n")
            raise e
        finally:
            # Close the browser
            driver.quit()
        return report_dir
    
    def _setup_bounty_folder(self, output_dir: str) -> str:
        ## TODO: Run create_bounty.sh script to create folder. Task dir name?
        return NotImplemented
    
    def _read_writeup(self, report_dir: str) -> str:
        bounty_id = report_dir.split("/")[-1]
        html_file_path = os.path.join(report_dir, f'{bounty_id}.html')
        try:
            with open(html_file_path, 'r', encoding='utf-8') as f:
                writeup = f.read()
        except FileNotFoundError:
            logger.warning(f"Writeup not found at: {html_file_path}")
            writeup = ""
        return writeup
    
    def _write_bounty_metadata(
            self, report_dir: str, import_bounty_message: ImportBountyMessage
    ):
        bounty_metadata_file_path = os.path.join(
            report_dir, "bounty_metadata.json"
        )

        # If it doesn't exist, create file and write metadata
        os.makedirs(os.path.dirname(bounty_metadata_file_path), exist_ok=True)
        with open(bounty_metadata_file_path, "w") as metadata_file:
            bounty_metadata = import_bounty_message.to_dict()
            json.dump(bounty_metadata, metadata_file)

        # Check if file was created
        if not os.path.exists(bounty_metadata_file_path):
            logger.error("Bounty metadata file not found")
            sys.exit(1)

        return

    def _extract_metadata(self, bounty_link: str, writeup: str) -> dict[str, str]:
        """
        Extracts the metadata from the bounty report
        """
        metadata = {}
        metadata['bounty_link'] = bounty_link
        metadata['CWE'] = self._extract_cwe(writeup)
        metadata['CVE'] = self._extract_cve(writeup)
        metadata['severity'] = self._extract_severity(writeup)
        metadata['disclosure_bounty'] = self._extract_disclosure_bounty(writeup)
        metadata['patch_bounty'] = self._extract_patch_bounty(writeup)
        metadata['vulnerable_commit'] = self._extract_vulnerable_commit(writeup)
        return metadata

    def _extract_bounty_link(self, writeup: str) -> str:
        """
        Extracts the bounty link from the writeup
        """
        soup = BeautifulSoup(writeup, 'html.parser')
        bounty_link_match = re.search(r'<!-- saved from url=\(\d+\)(https://huntr.com/bounties/[a-z0-9-]+) -->', writeup)
        if bounty_link_match:
            return bounty_link_match.group(1)
        else:
            return ""

    def _extract_cwe(self, writeup: str) -> str:
        """
        Extracts the CWE from the writeup
        """
        soup = BeautifulSoup(writeup, 'html.parser')
        cwe_element = soup.find('a', href=lambda href: href and "cwe.mitre.org" in href)
        if cwe_element:
            return str(cwe_element.text)
        return ""
    
    def _extract_cve(self, writeup: str) -> str:
        """
        Extracts the CVE from the writeup
        """
        soup = BeautifulSoup(writeup, 'html.parser')
        cve_element = soup.find('a', href=lambda href: href and "nvd.nist.gov" in href)
        if cve_element:
            return cve_element.text.strip()
        return ""
    
    def _extract_severity(self, writeup: str) -> str:
        """
        Extracts the severity from the writeup
        """
        soup = BeautifulSoup(writeup, 'html.parser')
        for tag in soup.find_all(string="Severity"):
            parent = tag.find_parent()
            if parent:
                severity_tag = parent.find_next(string=lambda text: "Critical" in text or "High" in text or "Medium" in text or "Low" in text)
                if severity_tag:
                    match = re.search(r'\((\d+\.\d+)\)', severity_tag)
                    if match:
                        return match.group(1)
        return ""
    
    def _extract_disclosure_bounty(self, writeup: str) -> str:
        """
        Extracts the disclosure bounty from the writeup
        """
        soup = BeautifulSoup(writeup, 'html.parser')
        for div in soup.find_all('div', class_='w-full font-medium'):
            if 'Disclosure Bounty' in div.text:
                # Extract the dollar amount
                bounty_tag = div.find('span', class_='opacity-50').find_next('span')
                if bounty_tag:
                    return bounty_tag.text.strip()
        return ""
    
    def _extract_patch_bounty(self, writeup: str) -> str:
        """
        Extracts the patch bounty from the writeup
        """
        soup = BeautifulSoup(writeup, 'html.parser')
        for div in soup.find_all('div', class_='w-full font-medium'):
            if 'Fix Bounty' in div.text:
                bounty_tag = div.find('span', class_='opacity-50')
                if bounty_tag:
                    return bounty_tag.text.strip()
        return ""
    
    def _extract_vulnerable_commit(self, writeup: str) -> str:
        """
        Extracts the vulnerable commit from the writeup
        """
        soup = BeautifulSoup(writeup, 'html.parser')
        affected_version_element = soup.find('span', text='Affected Version')
        if affected_version_element:
            affected_version_element = affected_version_element.find_next('p', class_='truncate opacity-50')
        if affected_version_element:
            return affected_version_element.text.strip()
        return ""
    
    def _parse_metadata_extraction(self, metadata: Dict[str, str]) -> ImportBountyMessage:
        """
        Parses the metadata dictionary into an ImportBountyMessage object.

        Args:
            metadata (Dict[str, str]): The metadata data.

        Returns:
            ImportBountyMessage: The parsed bounty message.

        Raises:
            TypeError: If metadata is not a dictionary.
            ExtractionParsingError: If required fields are missing or invalid.
        """
        if not isinstance(metadata, dict):
            raise TypeError("Metadata must be a dictionary.")
        
        required_fields = ['bounty_link', 'CWE', 'CVE', 'severity', 'disclosure_bounty', 'patch_bounty', 'vulnerable_commit']
        missing_fields = [field for field in required_fields if field not in metadata]
        if missing_fields:
            raise ValueError(
                f"Metadata is missing required fields: {', '.join(missing_fields)}"
            )
        
        bounty_link = metadata['bounty_link']
        cwe = metadata['CWE']
        cve = metadata['CVE']
        severity = metadata['severity']
        disclosure_bounty = metadata['disclosure_bounty']
        patch_bounty = metadata['patch_bounty']
        vulnerable_commit = metadata['vulnerable_commit']

        # TODO: handle optional fields

        # Example type checks (optional)
        if not isinstance(bounty_link, str):
            raise TypeError("bounty_link must be a string.")
        if not isinstance(cwe, str):
            raise TypeError("cwe must be a string.")
        if not isinstance(cve, str):
            raise TypeError("cve must be a string.")
        if not isinstance(severity, str):
            raise TypeError("severity must be a string.")
        if not isinstance(disclosure_bounty, str):
            raise TypeError("disclosure_bounty must be a string.")
        if not isinstance(patch_bounty, str):
            raise TypeError("patch_bounty must be a string.")
        if not isinstance(vulnerable_commit, str):
            raise TypeError("vulnerable_commit must be a string.")
        
        return ImportBountyMessage(
            agent_id=self.agent_id,
            message="Bounty metadata imported",
            success=True,
            bounty_link=bounty_link,
            cwe=cwe,
            cve=cve,
            severity=severity,
            disclosure_bounty=disclosure_bounty,
            patch_bounty=patch_bounty,
            detect_prompt_some_info="",
            detect_prompt_less_info="",
            exploit_prompt="",
            patch={},
            vulnerable_commit=vulnerable_commit,
        )