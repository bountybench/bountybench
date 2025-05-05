import json
import os
import re
import shutil
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def get_page_html(url):
    """Fetch the HTML content of a page using requests."""
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        page_html = response.text
        print(f"Successfully fetched HTML for {url}")
        return page_html
    except requests.exceptions.RequestException as e:
        print(f"Failed to get page HTML for {url}: {e}")
        return None


def is_valid_huntr_link(link):
    """Check if the link is in the desired format with only one component after 'https://huntr.com/bounties/'."""
    # Define the regular expression for a valid Huntr link format
    pattern = r"^https://huntr\.com/bounties/([a-f0-9\-]+)$"

    # Match the pattern
    return bool(re.match(pattern, link))


def setup_webdriver():
    """Set up the Chrome WebDriver using ChromeDriverManager."""
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.set_page_load_timeout(30)
    return driver


def save_html_for_links(driver, links, directory):
    """Save the HTML content of each linked page."""
    for i, link in enumerate(links):
        try:
            file_pattern = directory / f"report_{i}*"
            if any(
                file_path.match(file_pattern.name)
                for file_path in directory.glob(f"report_{i}*")
            ):
                print(
                    f"File starting with {file_pattern.name} already exists, skipping."
                )
                continue  # Skip this iteration if such a file exists

            driver.get(link)
            time.sleep(3)  # Wait for the page to load completely
            page_html = driver.page_source
            reported_date = extract_huntr_reported_date(page_html)
            if reported_date:
                save_path = directory / f"report_{i}_{reported_date}.html"
            else:
                save_path = directory / f"report_{i}.html"
            # Save the page's HTML content as a .html file
            with open(save_path, "w", encoding="utf-8") as file:
                file.write(page_html)

            print(f"Successfully saved HTML for {link} at {save_path}")
        except Exception as e:
            print(f"Failed to save page HTML for {link}: {e}")


def get_links_from_main_page(url):
    """Get all the Huntr report links from the main page."""
    try:
        page_html = get_page_html(url)
        if not page_html:
            return []

        soup = BeautifulSoup(page_html, "html.parser")
        report_links = soup.find_all("a", href=True, id="report-link")

        # Construct full URLs
        report_links = ["https://huntr.com" + link["href"] for link in report_links]
        valid_report_links = [
            link for link in report_links if is_valid_huntr_link(link)
        ]
        return list(set(valid_report_links))

    except Exception as e:
        print(f"Failed to get links from {url}: {e}")
        return []


def create_directory(directory):
    """Create a directory if it doesn't exist."""
    directory_path = Path(directory)
    directory_path.mkdir(parents=True, exist_ok=True)
    return directory_path


def get_huntr_repo_htmls(driver, repo_name, repo_dir):
    """Fetch and save HTML for all Huntr reports for a specific repo."""
    main_page_url = f"https://huntr.com/repos/{repo_name}"
    links = get_links_from_main_page(main_page_url)
    print("number of reports:", len(links))


# directory = create_directory(f"./html_writeups/{repo_dir}")
# save_html_for_links(driver, links, directory)


def extract_bounty_link_from_metadata(task_dir: str, bounty_number: str) -> str:
    """Extract the bounty link from the metadata JSON file."""
    task_dir = Path(task_dir)
    metadata_path = (
        task_dir / "bounties" / f"bounty_{bounty_number}" / "bounty_metadata.json"
    )

    if not metadata_path.exists():
        return None

    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
            return metadata.get("bounty_link")
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading metadata file: {e}")
        return None


def get_all_available_bounties(repo_name: str):
    source_dir = "bountybench"
    full_repo_dir = os.path.join(source_dir, repo_name)
    bounties_dir = os.path.join(full_repo_dir, "bounties")
    bounty_nums = [
        bounty_name.rsplit("_", 1)[1] for bounty_name in os.listdir(bounties_dir)
    ]
    return bounty_nums


def extract_huntr_repo_name(writeup: str) -> str:
    """Extract the repository name from the Huntr report HTML."""
    soup = BeautifulSoup(writeup, "html.parser")
    title = soup.find("h1", id="title")
    if title:
        link = title.find("a")
        if link:
            return link.get_text()
    return None


def extract_huntr_reported_date(writeup: str) -> str:
    """Extract the reported date from the Huntr report HTML and return it in MM_DD_YYYY format."""
    soup = BeautifulSoup(writeup, "html.parser")

    # Find the paragraph containing the "Reported on" text
    reported_date_element = soup.find(
        "p",
        class_="ml-3 mt-1 self-center text-xs font-medium text-white text-opacity-60",
    )

    if reported_date_element:
        # Example: "Reported on Sep 14th 2022"
        reported_date = reported_date_element.get_text(strip=True)

        # Extract month, day, and year
        parts = reported_date.split(" ")

        if len(parts) == 5:
            month_str = parts[2]
            day_str = parts[3].rstrip("thstndrd")
            year_str = parts[4]

            # Month to numeric mapping
            month_mapping = {
                "Jan": "01",
                "Feb": "02",
                "Mar": "03",
                "Apr": "04",
                "May": "05",
                "Jun": "06",
                "Jul": "07",
                "Aug": "08",
                "Sep": "09",
                "Oct": "10",
                "Nov": "11",
                "Dec": "12",
            }

            # Return the date in MM_DD_YYYY format
            return f"{month_mapping.get(month_str, '01')}_{day_str.zfill(2)}_{year_str}"

    return None


def read_huntr_writeup(task_dir: str, bounty_number: str) -> str:
    """Get the repository name from the metadata or the Huntr HTML content."""
    url = extract_bounty_link_from_metadata(task_dir, bounty_number)
    if not url:
        return None

    report_path = (
        Path(task_dir)
        / "bounties"
        / f"bounty_{bounty_number}"
        / "writeup"
        / "writeup.html"
    )
    if report_path.exists() and "huntr" in url:
        writeup = report_path.read_text(encoding="utf-8")
        return writeup
    return None


def is_report_valid(html):
    soup = BeautifulSoup(html, "html.parser")

    # Find the span with the desired title
    valid_span = soup.find(
        "span",
        class_="mr-1 text-xs font-medium border-super-bright-green text-super-bright-green bg-super-bright-green bg-opacity-20 rounded-full border px-2 py-1",
    )
    #  print(valid_span)
    if valid_span and "The report was marked as Valid" in valid_span.get("title", ""):
        return True
    return False


def get_all_writeups():
    """Main function to iterate over repositories and download HTMLs."""
    driver = setup_webdriver()
    source_dir = "bountybench"

    for repo_dir in os.listdir(source_dir):
        repo_dir = "lunary"
        full_repo_dir = os.path.join(source_dir, repo_dir)
        writeup = read_huntr_writeup(full_repo_dir, "0")
        repo_name = extract_huntr_repo_name(writeup)

        if repo_name:
            print(f"Repo name extracted: {repo_name}")
            get_huntr_repo_htmls(driver, repo_name, repo_dir)
        break
    driver.quit()


def filter_valid_writeups():
    source_dir = "html_writeups"
    dest_dir = "valid_html_writeups"
    os.makedirs(dest_dir, exist_ok=True)

    for repo_dir in os.listdir(source_dir):
        repo_path = os.path.join(source_dir, repo_dir)
        if os.path.isdir(repo_path):
            valid_counts = 0
            for file_name in os.listdir(repo_path):
                file_path = os.path.join(repo_path, file_name)
                file_path = Path(file_path)
                if file_path.exists() and os.path.isfile(file_path):

                    writeup = file_path.read_text(encoding="utf-8")
                    # Check if the report is valid
                    if is_report_valid(writeup):
                        valid_counts += 1
                        dest_repo_path = os.path.join(dest_dir, repo_dir)
                        # Ensure the repo directory exists in the destination folder
                        os.makedirs(dest_repo_path, exist_ok=True)
                        dest_file_path = os.path.join(dest_repo_path, file_name)
                        shutil.copy(file_path, dest_file_path)
        print(f"{repo_dir} number of valid reports: {valid_counts}")


def main():
    # get_all_writeups()
    filter_valid_writeups()


if __name__ == "__main__":
    main()
