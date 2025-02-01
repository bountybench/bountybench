import re
from selenium.webdriver.common.by import By
from .base_handler import BaseBountyHandler, logger

class HackerOneHandler(BaseBountyHandler):
    """
    HackerOneHandler is a class that handles the scraping of HackerOne bounty reports.
    """
    def wait_for_page_load(self):
        logger.info("Waiting for HackerOne timeline...")
        print("Waiting for HackerOne timeline...")
        self._wait_for_element(By.CSS_SELECTOR, 
            "div.timeline-item.activity.spec-activity")

    # HackerOne specific metadata extraction methods
    def extract_bounty_link(self) -> str:
        """Extract the HackerOne report URL"""
        # Look for meta tag with og:url content
        meta_url = self.soup.find('meta', property='og:url')
        if meta_url and meta_url.get('content'):
            return meta_url['content']
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
        cve_pattern = r'CVE-\d{4}-\d+'
        for text in self.soup.stripped_strings:
            match = re.search(cve_pattern, text)
            if match:
                return match.group(0)
        return ""

    def extract_severity(self) -> str:
        """Extract severity score from report"""
        # Look for severity indicators like CVSS scores
        severity_pattern = r'(?:CVSS|Severity)[:\s]+(\d+\.?\d*)'
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
                amount_match = re.search(r'\$(\d+(?:,\d+)?)', text)
                if amount_match:
                    return f"${amount_match.group(1)}"
        
        # Fallback to report ID if no bounty amount found
        report_id = self.bounty_link.split('/')[-1]
        return report_id

    def extract_patch_bounty(self) -> str:
        """Extract patch bounty information"""
        # For HackerOne, this might be version number or commit hash
        # Look for version patterns
        version_pattern = r'(?:version|v)\s*(\d+\.\d+\.\d+)'
        for text in self.soup.stripped_strings:
            match = re.search(version_pattern, text)
            if match:
                return match.group(1)
        return ""

    def extract_vulnerable_commit(self) -> str:
        """Extract vulnerable commit information"""
        # Look for commit hashes or version numbers
        commit_pattern = r'([a-f0-9]{40})'  # Full SHA-1 hash
        version_pattern = r'(?:version|v)\s*(\d+\.\d+\.\d+)'
        
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
        meta_url = self.soup.find('meta', property='og:url')
        return meta_url['content'] if meta_url else ""