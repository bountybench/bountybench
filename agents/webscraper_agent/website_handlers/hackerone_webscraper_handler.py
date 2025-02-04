import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from .webscraper_base_handler import WebscraperBaseHandler

class HackeroneWebscraperHandler(WebscraperBaseHandler):
    def __init__(self):
        super().__init__('hackerone')
        
    def get_latest_report_url(self) -> str:
        driver = webdriver.Chrome(options=self.chrome_options)
        try:
            driver.get("https://hackerone.com/hacktivity?querystring=&filter=type:public&order_direction=DESC&order_field=latest_disclosable_activity_at")
            wait = WebDriverWait(driver, 10)
            bounty_links = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='/reports/']"))
            )

            # Get first valid report URL
            for link in bounty_links:
                bounty_url = link.get_attribute('href')
                if bounty_url and '/reports/' in bounty_url:
                    if not bounty_url.startswith('https://hackerone.com'):
                        bounty_url = 'https://hackerone.com' + bounty_url
                    return bounty_url

            raise Exception("No valid bounty links found")

        except Exception as e:
            raise Exception(f"Error scraping HackerOne: {str(e)}")
        finally:
            driver.quit()