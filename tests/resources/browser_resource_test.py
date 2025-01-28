import os
import subprocess
import unittest
import logging
import shutil
from resources.browser_resource import BrowserResourceConfig, BrowserResource
from selenium.webdriver.common.by import By
from retrying import retry

# Configure logging
logging.basicConfig(level=logging.INFO)

class BrowserResourceTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @retry(stop_max_attempt_number=3, wait_fixed=1000)
    def test_chrome_connection(self):
        config = BrowserResourceConfig(
            browser = "chrome"
        )

        browser_resource = BrowserResource(resource_id="test_browser_resource", config=config)
        browser_resource.LoadPage("https://google.com")
        self.assertEqual(browser_resource.GetTitle(),"Google", "Incorrect title")

    @retry(stop_max_attempt_number=3, wait_fixed=1000)
    def test_chrome_get_interact(self):
        config = BrowserResourceConfig(
            browser = "chrome"
        )

        browser_resource = BrowserResource(resource_id="test_browser_resource", config=config)
        browser_resource.LoadPage("https://www.selenium.dev/selenium/web/web-form.html")
        
        text_box = browser_resource.GetElement(By.NAME, "my-text")
        submit_button = browser_resource.GetElement(By.CSS_SELECTOR, "button")
        text_box.send_keys("Selenium")
        submit_button.click()
        content = browser_resource.GetPage()
        print(content)
        self.assertTrue("Form submitted" in content, "Form not submitted")
        self.assertTrue("Received!" in content, "No received blurb")

        heading_elem = browser_resource.GetElement(By.CSS_SELECTOR, "h1")
        paragraph_elem = browser_resource.GetElement(By.CSS_SELECTOR, "p")
        
        self.assertEqual(heading_elem.text, "Form submitted", "Incorrect heading text after form submission")
        self.assertEqual(paragraph_elem.text, "Received!", "Incorrect paragraph text after form submission")

if __name__ == '__main__':
    unittest.main()