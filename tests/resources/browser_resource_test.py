import os
import subprocess
import unittest
import logging
import shutil
from resources.browser_resource import BrowserResourceConfig, BrowserResource
from selenium.webdriver.common.by import By
from retrying import retry
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO) 

class BrowserResourceTest(unittest.TestCase):

    def setUp(self):
        subprocess.run("./test_website/start_webserver.sh", shell=True)

    def tearDown(self):
        subprocess.run("./test_website/stop_webserver.sh", shell=True)

    @retry(stop_max_attempt_number=3, wait_fixed=1000)
    def test_chrome_connection(self):
        config = BrowserResourceConfig(
            browser = "chrome"
        )

        browser_resource = BrowserResource(resource_id="test_browser_resource", config=config)
        browser_resource.load_page("https://google.com")
        self.assertEqual(browser_resource.get_title(), "Google", "Incorrect title")

    @retry(stop_max_attempt_number=3, wait_fixed=1000)
    def test_chrome_get_interact(self):
        config = BrowserResourceConfig(
            browser = "chrome"
        )

        browser_resource = BrowserResource(resource_id="test_browser_resource", config=config)
        browser_resource.load_page("https://www.selenium.dev/selenium/web/web-form.html")
        
        text_box = browser_resource.get_element(By.NAME, "my-text")
        submit_button = browser_resource.get_element(By.CSS_SELECTOR, "button")
        text_box.send_keys("Selenium")
        submit_button.click()
        content = browser_resource.get_page()
        self.assertTrue("Form submitted" in content, "Form not submitted")
        self.assertTrue("Received!" in content, "No received blurb")

        heading_elem = browser_resource.get_element_with_css("h1")
        paragraph_elem = browser_resource.get_element_with_css("p")
        
        self.assertEqual(heading_elem.text, "Form submitted", "Incorrect heading text after form submission")
        self.assertEqual(paragraph_elem.text, "Received!", "Incorrect paragraph text after form submission")

    def test_local_get_interact(self):
        config = BrowserResourceConfig(
            browser = "chrome"
        )
        browser_resource = BrowserResource(resource_id="test_browser_resource", config=config)
        browser_resource.load_page("http://localhost:5000/form")
        content = browser_resource.get_page()
        self.assertTrue("Username" in content, "Form page not loaded")
        self.assertTrue(browser_resource.enter_text_in_field("name", "user"))
        self.assertTrue(browser_resource.click_element("submit"))
        content = browser_resource.get_page()
        self.assertTrue("Success" in content, "Success page not loaded") 

    def test_local_multiple_tabs(self):
        config = BrowserResourceConfig(
            browser = "chrome",
            tabs = 2
        )
        browser_resource = BrowserResource(resource_id="test_browser_resource", config=config)

        with self.assertRaises(Exception) as context:
            browser_resource.load_page("http://localhost:5000/form", 3)

        self.assertTrue('Invalid tab passed to load_page' in str(context.exception))

        browser_resource.load_page("http://localhost:5000/form", 1)
        browser_resource.load_page("http://localhost:5000/form", 2)

        content_tab_1 = browser_resource.get_page(tab = 1)
        content_tab_2 = browser_resource.get_page(tab = 2)

        self.assertTrue("Username" in content_tab_1, "Form page not loaded in tab 1")
        self.assertTrue("Username" in content_tab_2, "Form page not loaded in tab 2")

        self.assertTrue(browser_resource.enter_text_in_field("name", "user", tab = 1))
        self.assertTrue(browser_resource.enter_text_in_field("name", "bye", tab = 2))

        self.assertTrue(browser_resource.click_element("submit", tab=1))
        content_tab_1 = browser_resource.get_page(tab = 1)
        content_tab_2 = browser_resource.get_page(tab = 2)

        self.assertTrue("Success" in content_tab_1, "Success page not loaded for tab 1 when it should be") 
        self.assertFalse("Success" in content_tab_2, "Success page loaded for tab 2 when it should not be")

if __name__ == '__main__':
    unittest.main()