import os
from abc import ABC, abstractmethod
from typing import List

from selenium.webdriver.chrome.options import Options


class WebscraperBaseHandler(ABC):
    def __init__(self, website_name: str):
        self.website_name = website_name
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")

    @abstractmethod
    def get_latest_report_urls(self) -> List[str]:
        """Get the URL of the most recent public report."""
        pass

    def get_known_urls(self) -> set:
        """Get set of URLs that have already been found."""
        file_path = os.path.join(
            "agents/webscraper_agent/report_urls",
            f"{self.website_name}_report_urls.txt",
        )
        if not os.path.exists(file_path):
            return set()

        with open(file_path, "r") as f:
            return set(line.strip() for line in f if line.strip())

    def save_urls_to_file(self, urls: List[str]) -> None:
        """Save URL to appropriate urls file."""
        file_path = os.path.join(
            "agents/webscraper_agent/report_urls",
            f"{self.website_name}_report_urls.txt",
        )
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "a") as f:
            for url in urls:
                f.write(url + "\n")
