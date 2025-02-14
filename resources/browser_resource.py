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
from selenium.common.exceptions import WebDriverException

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
DEFAULT_NUM_TABS = 1

@dataclass
class BrowserResourceConfig(BaseResourceConfig):
    """Configuration for BrowserResourceConfig"""
    browser: str
    
    # Automatically wait for elements. See https://www.selenium.dev/documentation/webdriver/waits/ 
    wait: int = DEFAULT_WAIT_DURATION

    tabs: int = DEFAULT_NUM_TABS

    def validate(self) -> None:
        """
        Throws error if the config is not valid
        """
        if not self.browser or not self.browser in SUPPORTED_BROWSERS:
            raise ValueError("Browser is empty or invalid")
        if not self.wait or not self.wait >= 0:
            raise ValueError("Wait is empty or less than 0")
        if not self.tabs or not self.tabs >= 0:
            raise ValueError("Tabs is empty or less than 0")

class BrowserResource(BaseResource):

    def __init__(self, resource_id: str, config: BrowserResourceConfig):
        super().__init__(resource_id, config)
        
        self.drivers = []

        for i in range(config.tabs):
            if config.browser == "chrome":
                self.add_chrome_tab(config.wait)

    def close_tab(tab = 1):
        """
        Close tab

        Args:
           tab (int): tab to close
        """
        if (tab <= 0) or (tab > len(self.drivers)):
            raise Exception("Invalid tab passed to close_tab")

        self.drivers[tab-1].quit()
        self.drivers.pop(tab-1)

    def add_tab(config: BrowserResourceConfig):
        """
        Add a tab

        Args:
           config (BrowserResourceConfig) - configuration for the tab
        """
        if config.browser == "chrome":
            self.add_chrome_tab(config.wait)

    def add_chrome_tab(self, wait):
        """
        Add a chrome tab

        Args:
           wait (int) - Implicit wait time. See https://www.selenium.dev/documentation/webdriver/waits/
        """
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.implicitly_wait(wait)
        self.drivers.append(driver)

    def stop():
        for i in range(len(self.drivers)):
            self.drivers[i].quit()
        
    def load_page(self, url, tab = 1) -> None:
        """
        Loads a web page

        Args:
           url (str): the url (Ex: https://www.selenium.dev/selenium/web/web-form.html)
           tab (int): tab in which to load page
        """
        if (tab <= 0) or (tab > len(self.drivers)):
            raise Exception("Invalid tab passed to load_page")

        self.drivers[tab-1].get(url)
        return

    def get_title(self, tab = 1) -> str:
        """
        Returns the title of tab

        Args:
           tab (int): tab to get title from
        """
        if (tab <= 0) or (tab > len(self.drivers)):
            raise Exception("Invalid tab passed to get_title")

        return self.drivers[tab-1].title

    def get_page(self, url = '', tab = 1) -> str:
        """
        Returns the content of a web page. Pass in url if not already on page

        Args:
           url (str, optional): the url (Ex: https://www.selenium.dev/selenium/web/web-form.html)
           tab (int): tab to get content from
        """
        if (tab <= 0) or (tab > len(self.drivers)):
            raise Exception("Invalid tab passed to get_page")

        if url and self.drivers[tab-1].current_url != url:
           self.load_page(url, tab)

        return self.drivers[tab-1].page_source

    def get_element_with_id(self, val, tab = 1) -> WebElement:
        """
        Get an element using ID (See https://selenium-python.readthedocs.io/locating-elements.html#locating-by-id)

        Args:
            val (str): ID
            tab (int): tab in which to get the element
        """
        return self.get_element(By.ID, val, tab)

    def get_element_with_css(self, val, tab = 1) -> WebElement:
        """
        Get an element using CSS

        Args:
            val (str): CSS selector string (See https://selenium-python.readthedocs.io/locating-elements.html#locating-elements-by-css-selectors)
            tab (int): tab in which to get the element
        """
        return self.get_element(By.CSS_SELECTOR, val, tab)

    def get_element(self, by, val, tab = 1) -> WebElement:
        """
        Get an element (See https://selenium-python.readthedocs.io/locating-elements.html)

        Args:
            by (str): Locator Strategy (See: https://www.selenium.dev/selenium/docs/api/py/webdriver/selenium.webdriver.common.by.html)
            val (str): The value to search with in accordance with locator strategy
            tab (int): tab in which to get the element
        """
        if (tab <= 0) or (tab > len(self.drivers)):
            raise Exception("Invalid tab passed to get_element")

        return self.drivers[tab-1].find_element(by=by, value=val)

    def enter_text_in_field(self, id, text, tab = 1) -> bool:
        """
        Enter text into an input field

        Args:
            id (str): Id of the input field element in HTML
            text (str): Text to enter into element
            tab (int): tab in which to enter text for an element

        Returns:
           True if text was inserted into the input field, False otherwise
        """
        input_field = self.get_element_with_id(id, tab) 

        if not input_field or not input_field.is_enabled() or not input_field.is_displayed():
            return False

        input_field.send_keys(text)
        return True

    def click_element(self, id, tab = 1) -> bool:
        """
        Enter text into an input field

        Args:
            id (str): Id of the clickable element in HTML
            tab (int): tab in which to click the element

        Returns:
           True if button succesfully clicked, False otherwise
        """  

        try:
            element = self.get_element_with_id(id, tab)
            element.click()

        except WebDriverException:
            return False

        return True


    def get_driver(self, tab = 1) -> webdriver:
        """
        Args:
            tab (int): tab for which to get the driver for

        Returns the selenium web driver.

        Returns:
           The driver for custom processing
        """
        if (tab <= 0) or (tab > len(self.drivers)):
            raise Exception("Invalid tab passed to get_driver")

        return self.drivers[tab-1]
    
