import ast
import json
import requests
from typing import List

import validators

from agents.base_agent import BaseAgent
from responses.base_response import BaseResponse
from responses.response import Response
from utils.logger import get_main_logger
from agents.scraper_agent.web_scraper import scrape_dynamic_webpage

logger = get_main_logger(__name__)


class ScraperAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def run(self, responses: List[Response]) -> Response:
        pass
                
    
    def execute(self, urls: List[str]) -> Response:
        for url in urls:
            assert(validators.url(url))
            self.execute(url)
            scrape_dynamic_webpage(url)
            
        return BaseResponse("")