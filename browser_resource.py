from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

# Path to ChromeDriver
driver_path = "chromedriver-mac-arm64/chromedriver"

# Set up WebDriver
service = Service(driver_path)
driver = webdriver.Chrome(service=service)

try:
    # Navigate to the webpage
    url = "https://stanforddaily.com/"
    driver.get(url)
    print(f"Opened {url} successfully!")

    # Wait for the page to load
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    print("Page loaded successfully!")

    # Handle scrolling for lazy-loaded content
    SCROLL_PAUSE_TIME = 2
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # Scroll to the bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    # Extract all visible text from the page
    body_text = driver.find_element(By.TAG_NAME, "body").text
    print("Visible Text Extracted:\n", body_text)

    # Extract all raw HTML for further parsing
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, "html.parser")
    all_text = soup.get_text()
    print("All Text Extracted:\n", all_text)

    # Extract metadata
    page_title = driver.title
    print(f"Page Title: {page_title}")

    # Handle iframes
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for index, iframe in enumerate(iframes):
        driver.switch_to.frame(iframe)
        iframe_text = driver.find_element(By.TAG_NAME, "body").text
        print(f"IFrame {index + 1} Text: {iframe_text}")
        driver.switch_to.default_content()

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # Clean up and close the browser
    driver.quit()
    print("Browser closed.")
