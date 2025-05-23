from .hackerone_webscraper_handler import HackeroneWebscraperHandler
from .huntr_webscraper_handler import HuntrWebscraperHandler


class WebscraperHandlerFactory:
    @staticmethod
    def create_handler(website: str):
        if website == "https://huntr.com/bounties":
            return HuntrWebscraperHandler()
        elif website == "https://hackerone.com/reports/":
            return HackeroneWebscraperHandler()
        else:
            raise ValueError(f"Unsupported website: {website}")
