from typing import List
from agents.base_agent import BaseAgent
from responses.scraper_response import ScraperResponse
from responses.response import Response
from utils.logger import get_main_logger
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import validators 
import re


logger = get_main_logger(__name__)



class WebScraperAgent(BaseAgent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bounty_link = kwargs.get('bounty_link')
        self.bounty_program_name = self.extract_bounty_program_name(self.bounty_link)


    
    def run(self, responses: List[Response]) -> Response:

        if not self.is_valid_bounty_link():
            raise Exception(f"Invalid bounty_link {self.bounty_link}: The provided bounty link is not a valid URL.")
        else: 
            return self.extract_raw_html()
    
    def extract_raw_html(self) -> ScraperResponse:
        """
        Extracts the relevant information from the website
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--disable-dev-shm-usage', '--no-sandbox']
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            page = context.new_page()
            
            try:
                page.set_default_timeout(60000)
                page.set_default_navigation_timeout(60000)
                
                print("Navigating to page...")
                response = page.goto(self.bounty_link, wait_until='networkidle', timeout=60000)
                
                if response is None or not response.ok:
                    return ScraperResponse({'error': f"Failed to load page. Status: {response.status if response else 'Unknown'}"})
                
                print("Extracting raw HTML content...")
                raw_html = page.content()
                
                scraper_response = ScraperResponse(raw_html)
                scraper_response._bounty_program_name = self.bounty_program_name
                scraper_response._bounty_link = self.bounty_link
                return scraper_response

            except PlaywrightTimeout as e:
                raise TimeoutError(f"Timeout error: {str(e)}")
            except Exception as e:
                raise Exception(f"Error scraping {self.bounty_link}: {str(e)}")
            finally:
                browser.close()
    
    def extract_bounty_program_name(self, url):
        match = re.search(r'//(.*?)(?=\.com)', url)
        return match.group(1) if match else None
    
    def is_valid_bounty_link(self):
        return validators.url(self.bounty_link)