from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Dict, Tuple
import time

from utils.logger import get_main_logger

logger = get_main_logger(__name__)

class BaseBountyHandler:
    """
    BaseBountyHandler is a base class for all bounty handler classes.
    """
    def __init__(self, driver: webdriver.Chrome, writeup: str = None):
        self.driver = driver
        self.writeup = writeup
        self.soup = BeautifulSoup(writeup, 'html.parser') if writeup else None

    def _wait_for_element(self, by, identifier, timeout=30):
        try:
            logger.info(f"Waiting for element: {by}={identifier}")
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, identifier))
            )
            logger.info(f"Element found: {by}={identifier}")
        except Exception as e:
            logger.error(f"Wait for element timed out: {e}")
            raise

    def scroll_to_load_content(self):
        """Scroll to bottom of page to load all dynamic content"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def wait_for_page_load(self):
        """Wait for page-specific elements to load"""
        raise NotImplementedError

    def extract_metadata(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        raise NotImplementedError

    # Abstract methods for metadata extraction
    def extract_bounty_link(self) -> str:
        raise NotImplementedError

    def extract_cwe(self) -> str:
        raise NotImplementedError

    def extract_cve(self) -> str:
        raise NotImplementedError

    def extract_severity(self) -> str:
        raise NotImplementedError

    def extract_disclosure_bounty(self) -> str:
        raise NotImplementedError

    def extract_patch_bounty(self) -> str:
        raise NotImplementedError

    def extract_detect_prompt_some_info(self) -> str:
        """Extract detect prompt with some information"""
        return ""
    
    def extract_detect_prompt_less_info(self) -> str:
        """Extract detect prompt with less information"""
        return ""
    
    def extract_exploit_prompt(self) -> str:
        """Extract exploit prompt"""
        return ""
    
    def extract_patch(self) -> str:
        """Extract patch information"""
        return {}
    
    def extract_vulnerable_commit(self) -> str:
        raise NotImplementedError