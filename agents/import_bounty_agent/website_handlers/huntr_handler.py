import re
from typing import Dict, Tuple
from selenium.webdriver.common.by import By
from .base_handler import BaseBountyHandler


class HuntrHandler(BaseBountyHandler):
    """
    HuntrHandler is a class that handles the scraping of Huntr.com bounty reports.
    """

    def wait_for_page_load(self):
        self._wait_for_element(
            By.XPATH,
            "//iframe[@owner='archetype' and @title='archetype' and contains(@style, 'display')]",
        )

    # Metadata extraction methods
    def extract_bounty_link(self) -> str:
        bounty_link_match = re.search(
            r"<!-- saved from url=\(\d+\)(https://huntr.com/bounties/[a-z0-9-]+) -->",
            self.writeup,
        )
        return bounty_link_match.group(1) if bounty_link_match else ""

    def extract_cwe(self) -> str:
        cwe_element = self.soup.find(
            "a", href=lambda href: href and "cwe.mitre.org" in href
        )
        return str(cwe_element.text) if cwe_element else ""

    def extract_cve(self) -> str:
        cve_element = self.soup.find(
            "a", href=lambda href: href and "nvd.nist.gov" in href
        )
        return cve_element.text.strip() if cve_element else ""

    def extract_severity(self) -> str:
        for tag in self.soup.find_all(string="Severity"):
            parent = tag.find_parent()
            if parent:
                severity_tag = parent.find_next(
                    string=lambda text: "Critical" in text
                    or "High" in text
                    or "Medium" in text
                    or "Low" in text
                )
                if severity_tag:
                    match = re.search(r"\((\d+\.\d+)\)", severity_tag)
                    if match:
                        return match.group(1)
        return ""

    def extract_disclosure_bounty(self) -> str:
        for div in self.soup.find_all("div", class_="w-full font-medium"):
            if "Disclosure Bounty" in div.text:
                bounty_tag = div.find("span", class_="opacity-50").find_next("span")
                if bounty_tag:
                    return bounty_tag.text.strip()
        return ""

    def extract_patch_bounty(self) -> str:
        for div in self.soup.find_all("div", class_="w-full font-medium"):
            if "Fix Bounty" in div.text:
                bounty_tag = div.find("span", class_="opacity-50")
                if bounty_tag:
                    return bounty_tag.text.strip()
        return ""

    def extract_vulnerable_commit(self) -> str:
        affected_version_element = self.soup.find("span", text="Affected Version")
        if affected_version_element:
            affected_version_element = affected_version_element.find_next(
                "p", class_="truncate opacity-50"
            )
            if affected_version_element:
                return affected_version_element.text.strip()
        return ""

    def extract_metadata(self) -> Tuple[Dict[str, str], Dict[str, str]]:
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
