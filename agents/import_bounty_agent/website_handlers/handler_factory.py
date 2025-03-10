from typing import Optional
from selenium import webdriver
from .base_handler import BaseBountyHandler
from .huntr_handler import HuntrHandler
from .hackerone_handler import HackerOneHandler


def get_handler(
    website: str, driver: webdriver.Chrome, writeup: str = None
) -> Optional[BaseBountyHandler]:
    if website == "https://huntr.com/bounties":
        return HuntrHandler(driver, writeup)
    elif website == "https://hackerone.com/reports":
        return HackerOneHandler(driver, writeup)
    return None
