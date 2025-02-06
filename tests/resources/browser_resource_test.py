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
        browser_resource.LoadPage("https://google.com")
        self.assertEqual(browser_resource.GetTitle(), "Google", "Incorrect title")

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
        self.assertTrue("Form submitted" in content, "Form not submitted")
        self.assertTrue("Received!" in content, "No received blurb")

        heading_elem = browser_resource.GetElementWithCSS("h1")
        paragraph_elem = browser_resource.GetElementWithCSS("p")
        
        self.assertEqual(heading_elem.text, "Form submitted", "Incorrect heading text after form submission")
        self.assertEqual(paragraph_elem.text, "Received!", "Incorrect paragraph text after form submission")

    def test_local_get_interact(self):
        config = BrowserResourceConfig(
            browser = "chrome"
        )
        browser_resource = BrowserResource(resource_id="test_browser_resource", config=config)
        browser_resource.LoadPage("http://localhost:5000/form")
        content = browser_resource.GetPage()
        self.assertTrue("Username" in content, "Form page not loaded")
        self.assertTrue(browser_resource.EnterTextInField("name", "user"))
        self.assertTrue(browser_resource.ClickElement("submit"))
        content = browser_resource.GetPage()
        self.assertTrue("Success" in content, "Success page not loaded") 

if __name__ == '__main__':
    unittest.main()