import atexit
import os
import subprocess
import sys
import time
from resources.browser_resource import BrowserResourceConfig, BrowserResource
from googlesearch import search

from resources.browser_resource import BaseResource
from utils.logger import get_main_logger
import shutil

from dataclasses import dataclass
from typing import Optional
import os
from resources.base_resource import BaseResourceConfig

# Configure logging
logger = get_main_logger(__name__)
DEFAULT_SEARCH_CNT = 3

@dataclass
class SearchResourceConfig(BaseResourceConfig):
    search_result_count: int = DEFAULT_SEARCH_CNT 

    def validate(self) -> None:
        """
        Throws error if the config is not valid
        """
        if not self.search_result_count or not self.search_result_count >= 0:
            raise ValueError("Search result count is empty or less than 0")

class SearchResource(BaseResource):

    def __init__(self, resource_id: str, config: SearchResourceConfig):
        super().__init__(resource_id, config)
        self.search_result_count = config.search_result_count

        browser_config = BrowserResourceConfig(
            browser = "chrome"
        )
        self.__browser_resource = BrowserResource("search_browser_resource", config = browser_config)
            
    def stop():
        self.__browser_resource.stop()
        
    def GetSearchLinks(self, query, num_results = '') -> list[str]:
        """
        Run search on google.com and return the top `num_results` links

        Args:
            query (str): Search query for google.com
            num_results (int, optional): The number of links to return. Defaults to self.search_result_count
        """
        if not num_results:
            num_results = self.search_result_count

        results = []
        for result in search(query):
            if(result.startswith("https")):
                results.append(result)
                if(len(results) >= num_results):
                    break

        return results

   
    def Search(self, query, num_results = '') -> list[str]:
        """
        Run search on google.com and return the top `num_results` links

        Args:
            query (str): Search query for google.com
            num_results (int, optional): The number of links to return. Defaults to self.search_result_count
        """
        if not num_results:
            num_results = self.search_result_count

        links = self.GetSearchLinks(query, num_results)
        results = []
        for link in links:
            results.append(self.__browser_resource.GetPage(link))
        
        return results
    
