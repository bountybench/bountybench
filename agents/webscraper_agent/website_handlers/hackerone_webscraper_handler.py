from typing import List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from .webscraper_base_handler import WebscraperBaseHandler

class HackeroneWebscraperHandler(WebscraperBaseHandler):
    def __init__(self):
        super().__init__('hackerone')
        
    def get_latest_report_urls(self) -> List[str]:
        driver = webdriver.Chrome(options=self.chrome_options)
        try:
            driver.get("https://hackerone.com/hacktivity/overview?queryString=total_awarded_amount%3A%3E%3D1+AND+disclosed%3Atrue&sortField=latest_disclosable_activity_at&sortDirection=DESC&pageIndex=0")

            wait = WebDriverWait(driver, 10)
            report_links = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='/reports/']"))
            )

            # Get the latest report URLsL
            bounty_links = []
            for link in report_links:
                bounty_link = link.get_attribute('href')
                if bounty_link and '/reports/' in bounty_link:
                    if not bounty_link.startswith('https://hackerone.com'):
                        bounty_link = 'https://hackerone.com' + bounty_link
                    bounty_links.append(bounty_link)

            return bounty_links

        except Exception as e:
            raise Exception(f"Error scraping HackerOne: {str(e)}")
        finally:
            driver.quit()