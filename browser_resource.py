import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from resources.base_resource import BaseResource
from messages.action_messages.command_message import CommandMessage
from messages.parse_message import parse_field

class BrowserResource(BaseResource):
    """
    BrowserResource for automating browser interactions, exploring subpages,
    and changing site states (e.g., filling forms, clicking buttons).
    """

    def __init__(self, resource_id: str, config: dict):
        super().__init__(resource_id, config)
        self.driver = None
        self.scroll_pause_time = 2  # Time to wait during scrolling
        self.logger = self._setup_logger()

    def _setup_logger(self):
        """
        Sets up a logger for the resource.
        """
        logger = logging.getLogger(self._resource_id)
        if not logger.hasHandlers():
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger

    def init(self) -> None:
        """
        Initializes the browser resource by setting up the Selenium WebDriver.
        """
        driver_path = self._resource_config.get("driver_path", "chromedriver-mac-arm64/chromedriver")
        service = Service(driver_path)
        self.driver = webdriver.Chrome(service=service)
        self.logger.info("BrowserResource initialized successfully.")
    
    def _handle_scrolling(self) -> None:
        """
        Scrolls through the page to load dynamically loaded content.
        """
        self.logger.info("Scrolling through the page for lazy-loaded content...")

        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(self.scroll_pause_time)  # Wait for content to load

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break  # Stop if no new content loads

            last_height = new_height

    def _extract_page_data(self, url: str) -> dict:
        """
        Extracts data from a single webpage, including visible text, title, and links.

        :param url: The URL of the page to extract.
        :return: Dictionary with extracted page data.
        """
        self.driver.get(url)
        self.logger.info(f"Extracting data from {url}...")

        # Handle scrolling for lazy-loaded content
        self._handle_scrolling()

        # Extract visible text
        body_text = self.driver.find_element(By.TAG_NAME, "body").text

        # Extract metadata
        page_title = self.driver.title

        # Extract all links
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        links = [urljoin(url, link.get("href")) for link in soup.find_all("a", href=True)]

        return {
            "url": url,
            "title": page_title,
            "body_text": body_text,
            "links": links,
        }

    def run(self, message: dict) -> dict:
        """
        Parses the user's natural language command, extracts the relevant information,
        and executes the requested browser action.

        :param message: Dictionary containing the URL and command message.
        :return: Dictionary with extracted data and action results.
        """
        command_message = CommandMessage(resource_id=self._resource_id, message=message["message"])
        url = message.get("url")
        command = command_message.command.lower()  # Convert to lowercase for easier matching

        if not url:
            raise ValueError("The 'url' key must be provided in the message.")

        try:
            # Extract data from the main page
            main_page_data = self._extract_page_data(url)

            # Determine the action based on parsed command
            action_results = []
            if "fill form" in command or "submit" in command:
                result = self._handle_form_submission(command_message._message)
                action_results.append(result)

            elif "click button" in command or "press" in command:
                result = self._handle_button_click(command_message._message)
                action_results.append(result)

            elif "navigate" in command or "go to" in command:
                result = self._handle_navigation(command_message._message)
                action_results.append(result)

            else:
                return {"error": "Command not recognized. Supported commands: 'fill form', 'click button', 'navigate'."}

            # Return results
            return {
                "main_page": main_page_data,
                "actions_performed": action_results,
            }

        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            raise e

    def _handle_form_submission(self, message: str) -> dict:
        """
        Extracts form details from the message and fills the form.

        :param message: The user command message containing form details.
        :return: Result of the form submission.
        """
        form_selector = parse_field(message, "Form Selector:")
        form_data = self._extract_form_data(message)

        if not form_selector:
            return {"error": "Form selector missing. Please specify 'Form Selector:' followed by the correct identifier."}
        if not form_data:
            return {"error": "Form fields missing. Please specify field names and values (e.g., 'Name: John Doe')."}

        return self._fill_form(form_selector, form_data)

    def _extract_form_data(self, message: str) -> dict:
        """
        Extracts key-value pairs from the message related to form filling.

        :param message: The user command message containing form details.
        :return: A dictionary with form field names and their values.
        """
        fields = ["Name:", "Email:", "Username:", "Password:", "Phone:", "Address:"]
        form_data = {field.lower().rstrip(":"): parse_field(message, field) for field in fields if parse_field(message, field)}

        return form_data if form_data else None

    def _fill_form(self, form_selector: str, form_data: dict) -> dict:
        """
        Fills out a form on the webpage using the provided data.

        :param form_selector: The selector to identify the form (e.g., "form#login").
        :param form_data: Dictionary of form fields and their values.
        :return: Result of the form submission.
        """
        try:
            # Wait for the form to be present
            form = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, form_selector))
            )

            # Fill each form field
            for field_name, value in form_data.items():
                try:
                    field = form.find_element(By.NAME, field_name)
                    if field.tag_name == "input":
                        field.clear()
                        field.send_keys(value)
                    elif field.tag_name == "select":
                        select = Select(field)
                        select.select_by_value(value)
                    self.logger.info(f"Filled field '{field_name}' with value '{value}'.")
                except Exception as fe:
                    self.logger.warning(f"Could not fill field '{field_name}': {fe}")

            # Submit the form
            form.submit()
            self.logger.info("Form submitted successfully.")
            return {"action": "fill_form", "success": True}

        except Exception as e:
            self.logger.error(f"Error filling form: {e}")
            return {"action": "fill_form", "success": False, "error": str(e)}


    def _handle_button_click(self, message: str) -> dict:
        """
        Extracts button selector and performs a click.

        :param message: The user command message containing button details.
        :return: Result of the button click.
        """
        button_selector = parse_field(message, "Button Selector:")
        if not button_selector:
            return {"error": "Button selector missing. Please specify 'Button Selector:' followed by the button ID."}

        return self._click_button(button_selector)

    def _handle_navigation(self, message: str) -> dict:
        """
        Extracts navigation URL and directs the browser.

        :param message: The user command message containing navigation details.
        :return: Result of the navigation.
        """
        navigate_url = parse_field(message, "Navigate To:")
        if not navigate_url:
            return {"error": "Navigation URL missing. Please specify 'Navigate To:' followed by a valid URL."}

        self.driver.get(navigate_url)
        self.logger.info(f"Navigated to {navigate_url}")
        return {"action": "navigate", "success": True}

    def stop(self) -> None:
        """
        Stops the browser resource and closes the Selenium WebDriver.
        """
        if self.driver:
            self.driver.quit()
            self.logger.info("BrowserResource stopped and WebDriver closed.")