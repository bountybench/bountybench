import json
import os
from pathlib import Path

import requests
from bs4 import BeautifulSoup


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


def save_html_for_links(links, directory):
    """Save the HTML content of each linked page."""
    for i, link in enumerate(links):
        save_path = directory / f"report_{i + 1}.html"
        page_html = get_page_html(link)

        if page_html:
            with open(save_path, "w", encoding="utf-8") as file:
                file.write(page_html)
            print(f"Saved {link} as {save_path}")
        else:
            print(f"Failed to fetch HTML for {link}")


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
        print(report_links)
        return report_links

    except Exception as e:
        print(f"Failed to get links from {url}: {e}")
        return []


def create_directory(directory):
    """Create a directory if it doesn't exist."""
    directory_path = Path(directory)
    directory_path.mkdir(parents=True, exist_ok=True)
    return directory_path


def get_huntr_repo_htmls(repo_name, repo_dir):
    """Fetch and save HTML for all Huntr reports for a specific repo."""
    main_page_url = f"https://huntr.com/repos/{repo_name}"
    links = get_links_from_main_page(main_page_url)

    directory = create_directory(f"./html_writeups/{repo_dir}")
    save_html_for_links(links, directory)


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


def extract_huntr_repo_name(writeup: str) -> str:
    """Extract the repository name from the Huntr report HTML."""
    soup = BeautifulSoup(writeup, "html.parser")
    title = soup.find("h1", id="title")
    if title:
        link = title.find("a")
        if link:
            return link.get_text()
    return None


def get_repo_name(task_dir: str, bounty_number: str) -> str:
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
        return extract_huntr_repo_name(writeup)
    return None


def main():
    """Main function to iterate over repositories and download HTMLs."""
    source_dir = "bountybench"

    for repo_dir in os.listdir(source_dir):
        full_repo_dir = os.path.join(source_dir, repo_dir)
        repo_name = get_repo_name(full_repo_dir, "0")

        if repo_name:
            print(f"Repo name extracted: {repo_name}")
            get_huntr_repo_htmls(repo_name, repo_dir)


if __name__ == "__main__":
    main()
