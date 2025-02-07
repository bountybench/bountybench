import os
from typing import List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from .webscraper_base_handler import WebscraperBaseHandler

class HuntrWebscraperHandler(WebscraperBaseHandler):
    def __init__(self):
        super().__init__('huntr')

    def get_latest_report_urls(self) -> List[str]:
        driver = webdriver.Chrome(options=self.chrome_options)
        try:
            driver.get("https://huntr.com/bounties/hacktivity")
            wait = WebDriverWait(driver, 10)
            report_links = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href^='/bounties/']"))
            )

            if not report_links:
                raise Exception("No bounty links found")

            # Get the latest report URLs
            bounty_links = []
            for link in report_links:
                bounty_link = link.get_attribute("href")
                if "/bounties/disclose" not in bounty_link:
                    if not bounty_link.startswith("https://huntr.com"):
                        bounty_link = "https://huntr.com" + bounty_link
                    bounty_links.append(bounty_link)

            return bounty_links
        
        except Exception as e:
            raise Exception(f"Error scraping Huntr: {str(e)}")
        finally:
            driver.quit()