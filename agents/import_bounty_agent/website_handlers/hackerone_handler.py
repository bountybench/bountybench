import base64
import os
import re
from typing import Dict, Tuple
from dotenv import load_dotenv
import requests
from selenium.webdriver.common.by import By
from .base_handler import BaseBountyHandler, logger


class HackerOneHandler(BaseBountyHandler):
    """
    HackerOneHandler is a class that handles the scraping of HackerOne bounty reports.
    """

    def wait_for_page_load(self):
        self._wait_for_element(
            By.CSS_SELECTOR, "div.timeline-item.activity.spec-activity"
        )

    # Extract metadata with API
    def extract_metadata(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        load_dotenv()
        hackerone_api_key = os.getenv("HACKERONE_API_KEY").strip('"')
        hackerone_api_identifier = os.getenv("HACKERONE_API_IDENTIFIER").strip('"')

        # Create Basic auth header
        credentials = f"{hackerone_api_identifier}:{hackerone_api_key}"
        encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode(
            "utf-8"
        )

        headers = {
            "Accept": "application/json",
            "Authorization": f"Basic {encoded_credentials}",
        }

        # Get report ID from bounty link
        report_id = self.bounty_link.split("/")[-1]

        # Fetch report data from HackerOne API
        response = requests.get(
            f"https://api.hackerone.com/v1/reports/{report_id}", headers=headers
        )
        logger.info(f"Fetched report data for {report_id}")

        # Check if the request was successful
        if response.status_code != 200:
            logger.error(
                f"Failed to fetch report data for {report_id}: {response.status_code} {response.text}"
            )
            return self.extract_metadata_from_html(), None
        else:
            report_data = response.json()
            return self.extract_metadata_from_api_data(report_data), report_data

    def extract_metadata_from_api_data(
        self, report_data: Dict[str, str]
    ) -> Dict[str, str]:

        attributes = report_data["data"]["attributes"]
        relationships = report_data["data"]["relationships"]

        # Extract bounty information
        bounty_amount = next(
            (
                bounty["attributes"].get("awarded_amount")
                for bounty in relationships.get("bounties", {}).get("data", [])
                if bounty.get("attributes", {}).get("awarded_amount")
            ),
            None,
        )

        # Extract weakness (CWE) information
        weakness = (
            relationships.get("weakness", {}).get("data", {}).get("attributes", {})
        )

        return {
            "bounty_link": f"https://hackerone.com/reports/{report_data['data']['id']}",
            "CWE": weakness.get("external_id"),  # This will be in format "CWE-XXX"
            "CVE": ", ".join(attributes.get("cve_ids", [])),
            "severity": relationships.get("severity", {})
            .get("data", {})
            .get("attributes", {})
            .get("rating"),
            "disclosure_bounty": str(bounty_amount) if bounty_amount else None,
            "patch_bounty": None,  # Not directly available in API
            "detect_prompt_some_info": attributes.get("detect_prompt_some_info"),
            "detect_prompt_less_info": attributes.get("detect_prompt_less_info"),
            "exploit_prompt": attributes.get("exploit_prompt"),
            "patch": attributes.get("patch"),
            "vulnerability_commit": attributes.get("vulnerability_information"),
        }

    # HackerOne specific metadata extraction methods
    def extract_bounty_link(self) -> str:
        """Extract the HackerOne report URL"""
        # Look for meta tag with og:url content
        meta_url = self.soup.find("meta", property="og:url")
        if meta_url and meta_url.get("content"):
            return meta_url["content"]
        return ""

    def extract_cwe(self) -> str:
        """Extract CWE from report title or content"""
        # First try to find CWE in any text content
        cwe_pattern = r'CWE-\d+:?\s+([^"\n]+)'
        for text in self.soup.stripped_strings:
            match = re.search(cwe_pattern, text)
            if match:
                return f"CWE-{match.group(1)}"
        return ""

    def extract_cve(self) -> str:
        """Extract CVE from report title or content"""
        # Look for CVE pattern in text
        cve_pattern = r"CVE-\d{4}-\d+"
        for text in self.soup.stripped_strings:
            match = re.search(cve_pattern, text)
            if match:
                return match.group(0)
        return ""

    def extract_severity(self) -> str:
        """Extract severity score from report"""
        # Look for severity indicators like CVSS scores
        severity_pattern = r"(?:CVSS|Severity)[:\s]+(\d+\.?\d*)"
        for text in self.soup.stripped_strings:
            match = re.search(severity_pattern, text)
            if match:
                return match.group(1)
        return ""

    def extract_disclosure_bounty(self) -> str:
        """Extract disclosure bounty amount"""
        # Look for bounty amount in timeline entries
        bounty_text = "This bounty was awarded with"
        for text in self.soup.stripped_strings:
            if bounty_text in text:
                # Extract the dollar amount
                amount_match = re.search(r"\$(\d+(?:,\d+)?)", text)
                if amount_match:
                    return f"${amount_match.group(1)}"

        # Fallback to report ID if no bounty amount found
        report_id = self.bounty_link.split("/")[-1]
        return report_id

    def extract_patch_bounty(self) -> str:
        """Extract patch bounty information"""
        # For HackerOne, this might be version number or commit hash
        # Look for version patterns
        version_pattern = r"(?:version|v)\s*(\d+\.\d+\.\d+)"
        for text in self.soup.stripped_strings:
            match = re.search(version_pattern, text)
            if match:
                return match.group(1)
        return ""

    def extract_vulnerable_commit(self) -> str:
        """Extract vulnerable commit information"""
        # Look for commit hashes or version numbers
        commit_pattern = r"([a-f0-9]{40})"  # Full SHA-1 hash
        version_pattern = r"(?:version|v)\s*(\d+\.\d+\.\d+)"

        for text in self.soup.stripped_strings:
            # First try to find commit hash
            commit_match = re.search(commit_pattern, text)
            if commit_match:
                return commit_match.group(1)

            # Then try version number
            version_match = re.search(version_pattern, text)
            if version_match:
                return version_match.group(1)

        return ""

    @property
    def bounty_link(self) -> str:
        """Helper to get bounty link from meta tags"""
        meta_url = self.soup.find("meta", property="og:url")
        return meta_url["content"] if meta_url else ""

    def extract_metadata_from_html(self) -> Dict[str, str]:
        """Extract all metadata fields"""
        if not self.soup:
            raise ValueError("No HTML content loaded for extraction")

        return (
            {
                "bounty_link": self.extract_bounty_link(),
                "CWE": self.extract_cwe(),
                "CVE": self.extract_cve(),
                "severity": self.extract_severity(),
                "disclosure_bounty": self.extract_disclosure_bounty(),
                "patch_bounty": self.extract_patch_bounty(),
                "detect_prompt_some_info": self.extract_detect_prompt_some_info(),
                "detect_prompt_less_info": self.extract_detect_prompt_less_info(),
                "exploit_prompt": self.extract_exploit_prompt(),
                "patch": self.extract_patch(),
                "vulnerable_commit": self.extract_vulnerable_commit(),
            },
            None,
        )
