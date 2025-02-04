import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from .webscraper_base_handler import WebscraperBaseHandler

class HuntrWebscraperHandler(WebscraperBaseHandler):
    def __init__(self):
        super().__init__('huntr')

    def get_latest_report_url(self) -> str:
        driver = webdriver.Chrome(options=self.chrome_options)
        try:
            driver.get("https://huntr.com/bounties/hacktivity")
            wait = WebDriverWait(driver, 10)
            bounty_links = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href^='/bounties/']"))
            )

            # Ensure the first valid bounty link is selected (ignoring "/bounties/disclose")
            for link in bounty_links:
                bounty_url = link.get_attribute("href")
                if "/bounties/disclose" not in bounty_url:
                    if not bounty_url.startswith("https://huntr.com"):
                        bounty_url = "https://huntr.com" + bounty_url
                    return bounty_url
            
            raise Exception("No valid bounty links found")
                
        finally:
            driver.quit()