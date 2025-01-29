import atexit
import os
import subprocess
import sys
import time
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from googlesearch import search

from resources.base_resource import BaseResource
from utils.logger import get_main_logger
import shutil

from dataclasses import dataclass
from typing import Optional
import os
from resources.base_resource import BaseResourceConfig

# Configure logging
logger = get_main_logger(__name__)
SUPPORTED_BROWSERS = ["chrome"]
DEFAULT_WAIT_DURATION = 5
DEFAULT_SEARCH_CNT = 3

@dataclass
class BrowserResourceConfig(BaseResourceConfig):
    """Configuration for BrowserResourceConfig"""
    browser: str
    
    # Automatically wait for elements. See https://www.selenium.dev/documentation/webdriver/waits/ 
    wait: int = DEFAULT_WAIT_DURATION

    search_result_count: int = DEFAULT_SEARCH_CNT 

    def validate(self) -> None:
        """
        Throws error if the config is not valid
        """
        if not self.browser or not self.browser in SUPPORTED_BROWSERS:
            raise ValueError("Browser is empty or invalid")
        if not self.wait or not self.wait >= 0:
            raise ValueError("Wait is empty or less than 0")
        if not self.search_result_count or not self.search_result_count >= 0:
            raise ValueError("Search result count is empty or less than 0")

class BrowserResource(BaseResource):

    def __init__(self, resource_id: str, config: BrowserResourceConfig):
        super().__init__(resource_id, config)
        self.search_result_count = config.search_result_count

        if config.browser == "chrome":
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            self.driver.implicitly_wait(config.wait)
            

    def stop():
        self.driver.quit()
        
    def LoadPage(self,url) -> None:
        """
        Loads a web page

        Args:
           url (str): the url (Ex: https://www.selenium.dev/selenium/web/web-form.html)
        """
        self.driver.get(url)
        return

    def GetTitle(self) -> str:
        return self.driver.title

    def GetPage(self, url = '') -> str:
        """
        Returns the content of a web page. Pass in url if not already on page

        Args:
           url (str, optional): the url (Ex: https://www.selenium.dev/selenium/web/web-form.html)
        """
        if url and self.driver.current_url != url:
           self.LoadPage(url)

        return self.driver.page_source

    def GetElementWithID(self, val) -> WebElement:
        """
        Get an element using ID (See https://selenium-python.readthedocs.io/locating-elements.html#locating-by-id)

        Args:
            val (str): ID
        """
        return self.GetElement(By.ID, val)

    def GetElementWithCSS(self, val) -> WebElement:
        """
        Get an element using CSS

        Args:
            val (str): CSS selector string (See https://selenium-python.readthedocs.io/locating-elements.html#locating-elements-by-css-selectors)
        """
        return self.GetElement(By.CSS_SELECTOR, val)

    def GetElement(self, by, val) -> WebElement:
        """
        Get an element (See https://selenium-python.readthedocs.io/locating-elements.html)

        Args:
            by (str): Locator Strategy (See: https://www.selenium.dev/selenium/docs/api/py/webdriver/selenium.webdriver.common.by.html)
            val (str): The value to search with in accordance with locator strategy
        """
        return self.driver.find_element(by=by, value=val)

    def getDriver(self) -> webdriver:
        """
        Returns the selenium web driver.

        Returns:
           The driver for custom processing
        """
        return self.driver

    def search(self, query, num_results = '') -> list[str]:
        """
        Run search on google.com and return the top `num_results` links

        Args:
            query (str): Search query for google.com
            num_results (int, optional): The number of links to return. Defaults to self.search_result_count
        """
        if not num_results:
            num_results = self.search_result_count

        results = []
        for result in search(query, num_results=num_results):
            results.append(result)

        return results
    
