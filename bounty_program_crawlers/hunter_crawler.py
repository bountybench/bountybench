from playwright.sync_api import sync_playwright
import time
import json
import random

def random_delay(min_time=2, max_time=10):
    """Introduce a random delay to mimic human behavior."""
    time.sleep(random.uniform(min_time, max_time))

def run(playwright):
    # Define the user agent options
    user_agent_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36"
    ]

    # Create a browser context with a random user agent
    context = playwright.chromium.launch(headless=True).new_context(
        user_agent=random.choice(user_agent_list)
    )
    page = context.new_page()

    page.goto("https://huntr.com/bounties")
    page.wait_for_selector('select[name="location"]')

    page.select_option('select[name="location"]', 'list')

    random_delay()  # Introduce random delay

    links = page.query_selector_all('a.hover\\:text-blue-400')
    base_url = "https://huntr.com"

    sponsor_data = []
    for link in links:
        try:
            bounty_sponsor_link = base_url + link.get_attribute('href')
            bounty_sponsor_name = link.text_content()
            sponsor_data.append((bounty_sponsor_name, bounty_sponsor_link))
        except Exception as e:
            print(f"Error processing link: {e}")
            continue

    bounty_list = []  # List to store all bounty dictionaries

    for bounty_sponsor_name, bounty_sponsor_link in sponsor_data:
        bounty_dict = {}
        bounty_dict["sponsor_name"] = bounty_sponsor_name
        bounty_dict["sponsor_link"] = bounty_sponsor_link
        page.goto(bounty_sponsor_link)
        random_delay(5, 15)  # Random delay to avoid fast requests

        try:
            bounty_sponsor_github_link = page.query_selector('a.ml-5.self-center.text-2xl.font-bold.text-white.hover\\:text-blue-400').get_attribute('href')
            bounty_dict["sponsor_github_link"] = bounty_sponsor_github_link
            bounty_sponsor_description = page.query_selector('p.self-center.overflow-scroll.text-sm.text-white.text-opacity-60').text_content()
            bounty_dict["sponsor_description"] = bounty_sponsor_description

        except Exception as e:
            print(f"Error fetching bounty details: {e}")
            continue

        bounty_sponsor_information = page.query_selector_all('div.mt-1\\.5.flex.flex-row.text-xs')
        bounty_dict["sponsor_interaction_info"] = []
        for heading in bounty_sponsor_information:
            try:
                info_heading = heading.query_selector('h4').text_content()
                info_value = heading.query_selector('h4.ml-auto').text_content()
                bounty_dict["sponsor_interaction_info"].append({f"{info_heading}": info_value})
            except Exception as e:
                print(f"Error processing bounty sponsor information: {e}")

        bounty_sponsor_dollar_information = page.query_selector_all("div.mt-1\\.5.flex.flex-col.text-xs")
        bounty_dict["sponsor_dollar_info"] = []
        for heading in bounty_sponsor_dollar_information:
            try:
                dollar_heading = heading.query_selector('h4').text_content()
                dollar_value = heading.query_selector('h4.opacity-50').text_content()
                bounty_dict["sponsor_dollar_info"].append({f"{dollar_heading}": dollar_value})
            except Exception as e:
                print(f"Error processing dollar information: {e}")

        individual_bounty_links = page.query_selector_all("#report-link")
        bounty_dict["bounty_links"] = []
        if individual_bounty_links:
            for bounty_link in individual_bounty_links:
                try:
                    individual_bounty_link = base_url + bounty_link.get_attribute('href')
                    bounty_dict["bounty_links"].append(individual_bounty_link)
                except Exception as e:
                    print(f"Error processing individual bounty link: {e}")

        bounty_list.append(bounty_dict)
        print(bounty_dict)
        print("==================================")

    # Save bounty_list to a JSON file
    with open("hunter_io_bounties.json", "w") as json_file:
        json.dump(bounty_list, json_file, indent=4)

    random_delay(5000, 7000)  # Longer random sleep period before closing
    context.close()  # Close the context to release resources properly

with sync_playwright() as playwright:
    run(playwright)