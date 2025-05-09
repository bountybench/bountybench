import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
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

    def get_known_urls(self, bounty_dir: str) -> set:
        """Get set of URLs that have already been found."""
        file_path = os.path.join(
            f"{bounty_dir}/report_urls",
            f"{self.website_name}_report_urls.json",
        )
        if not os.path.exists(file_path):
            return set()

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                # Handle data as a dictionary with URLs as keys
                return set(
                    url for url, info in data.items() if info.get("imported", False)
                )
        except (json.JSONDecodeError, FileNotFoundError):
            return set()

    def save_urls_to_file(self, urls: List[str], bounty_dir: str) -> None:
        """
        Save URLs to a JSON file with metadata.
        """
        file_path = os.path.join(
            f"{bounty_dir}/report_urls",
            f"{self.website_name}_report_urls.json",
        )
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Read existing data if file exists
        existing_data = {}
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = {}

        # Add new URLs with metadata
        timestamp = datetime.now().isoformat()
        for url in urls:
            if url not in existing_data:
                existing_data[url] = {
                    "url": url,
                    "timestamp": timestamp,
                    "website": self.website_name,
                    "imported": False,
                }

        # Write to file
        with open(file_path, "w") as f:
            json.dump(existing_data, f, indent=2)
