import logging
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from resources.base_resource import BaseResource


class BrowserResource(BaseResource):
    """
    BrowserResource for automating browser interactions, detecting forms dynamically,
    clicking buttons, and navigating pages.
    """

    def __init__(self, resource_id: str, config: dict):
        super().__init__(resource_id, config)
        self.driver = None
        self.scroll_pause_time = 2  # Time to wait during scrolling
        self.logger = self._setup_logger()

    def _setup_logger(self):
        """Sets up a logger for the resource."""
        logger = logging.getLogger(self._resource_id)
        if not logger.hasHandlers():  # Avoid duplicate handlers
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger

    def init(self) -> None:
        """Initializes the browser resource by setting up the Selenium WebDriver."""
        driver_path = self._resource_config.get("driver_path", "chromedriver-mac-arm64/chromedriver")
        service = Service(driver_path)
        self.driver = webdriver.Chrome(service=service)
        self.logger.info("BrowserResource initialized successfully.")

    def run(self, message: dict) -> dict:
        """
        Executes the task of interacting with a webpage, detecting elements, and changing site state.

        :param message: Dictionary containing the URL, actions, inputs, and subpage exploration options.
        :return: Dictionary with extracted data and action results.
        """
        url = message.get("url")
        actions = message.get("actions", [])
        inputs = message.get("inputs", {})

        if not url:
            raise ValueError("The 'url' key must be provided in the message.")

        try:
            main_page_data = self._extract_page_data(url)
            action_results = [self._perform_action(action, inputs) for action in actions]

            return {
                "main_page": main_page_data,
                "actions_performed": action_results
            }

        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            raise e

    def _perform_action(self, action: str, inputs: dict) -> dict:
        """
        Performs a specific action on the webpage (e.g., fill form, click button, navigate).
        Automatically detects forms if no selector is provided.

        :param action: The type of action to perform (e.g., "fill_form", "click_button").
        :param inputs: The inputs required for the action.
        :return: Result of the action.
        """
        try:
            if action == "fill_form":
                form_selector = inputs.get("form_selector") or self._detect_form_selector()
                if not form_selector:
                    return {"action": "fill_form", "success": False, "error": "No form detected on page."}

                form_data = inputs.get("form_data", {})
                return self._fill_form(form_selector, form_data)

            elif action == "click_button":
                button_selector = inputs.get("button_selector") or self._detect_button_selector()
                if not button_selector:
                    return {"action": "click_button", "success": False, "error": "No button detected on page."}

                return self._click_button(button_selector)

            elif action == "navigate":
                navigate_to = inputs.get("navigate_to")
                if not navigate_to:
                    return {"action": "navigate", "success": False, "error": "Navigation URL missing."}

                return self._navigate(navigate_to)

            else:
                return {"action": action, "success": False, "error": "Unsupported action"}

        except Exception as e:
            self.logger.error(f"Error performing action '{action}': {e}")
            return {"action": action, "success": False, "error": str(e)}

    def _detect_form_selector(self):
        """Automatically detects the most relevant form on the page."""
        try:
            forms = self.driver.find_elements(By.TAG_NAME, "form")
            if not forms:
                return None

            # Pick the form with the most input fields
            best_form = max(forms, key=lambda form: len(form.find_elements(By.TAG_NAME, "input")), default=None)

            if best_form:
                form_id = best_form.get_attribute("id")
                form_class = best_form.get_attribute("class")
                return f"form[id='{form_id}']" if form_id else f"form[class='{form_class.split()[0]}']" if form_class else "form"

        except Exception as e:
            self.logger.error(f"Error detecting form: {e}")
            return None

    def _detect_button_selector(self):
        """Automatically detects the most relevant button on the page."""
        try:
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            if not buttons:
                return None
            return "button[type='submit']"  # Defaulting to submit buttons

        except Exception as e:
            self.logger.error(f"Error detecting button: {e}")
            return None

    def _fill_form(self, form_selector: str, form_data: dict) -> dict:
        """Fills out a form dynamically using detected selectors."""
        try:
            form = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, form_selector))
            )

            for field_name, value in form_data.items():
                try:
                    field = form.find_element(By.NAME, field_name)
                    field.clear()
                    field.send_keys(value)
                    self.logger.info(f"Filled '{field_name}' with '{value}'.")
                except:
                    self.logger.warning(f"Field '{field_name}' not found.")

            form.submit()
            self.logger.info("Form submitted successfully.")
            return {"action": "fill_form", "success": True}

        except Exception as e:
            self.logger.error(f"Error filling form: {e}")
            return {"action": "fill_form", "success": False, "error": str(e)}

    def _click_button(self, button_selector: str) -> dict:
        """Clicks a button on the page dynamically."""
        try:
            button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, button_selector))
            )
            button.click()
            self.logger.info(f"Clicked button: {button_selector}")
            return {"action": "click_button", "success": True}

        except Exception as e:
            self.logger.error(f"Error clicking button: {e}")
            return {"action": "click_button", "success": False, "error": str(e)}

    def _navigate(self, url: str) -> dict:
        """Navigates to a different page."""
        try:
            self.driver.get(url)
            self.logger.info(f"Navigated to {url}")
            return {"action": "navigate", "success": True}
        except Exception as e:
            self.logger.error(f"Error navigating to {url}: {e}")
            return {"action": "navigate", "success": False, "error": str(e)}

    def _extract_page_data(self, url: str) -> dict:
        """Extracts page text, title, and links."""
        self.driver.get(url)
        self.logger.info(f"Extracting data from {url}...")

        self._handle_scrolling()
        body_text = self.driver.find_element(By.TAG_NAME, "body").text
        page_title = self.driver.title
        links = [urljoin(url, a.get_attribute("href")) for a in self.driver.find_elements(By.TAG_NAME, "a") if a.get_attribute("href")]

        return {"url": url, "title": page_title, "body_text": body_text, "links": links}

    def _handle_scrolling(self):
        """Scrolls to load dynamic content."""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(self.scroll_pause_time)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def stop(self) -> None:
        """Stops and closes the browser."""
        if self.driver: 
            self.driver.quit()
            self.logger.info("BrowserResource stopped.")
