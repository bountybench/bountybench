import json
import requests
from typing import List

import urllib.parse

from agents.base_agent import BaseAgent
from responses.base_response import BaseResponse
from responses.response import Response
from utils.logger import get_main_logger


logger = get_main_logger(__name__)


class ScraperAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def run(self, responses: List[Response]) -> Response:
        
        sample_url = "https://huntr.com/bounties/95d8b993-3347-4ef5-a2b3-1f57219b7871"
        bounty_id = "95d8b993-3347-4ef5-a2b3-1f57219b7871"
        return self.execute(sample_url, bounty_id)
    

    # question, is run the "workflow" of scraper or just for 1 url? Do we need a url resp?
    # assume it does some additional handling, so execute will actuall scrape url
    def execute(self, url: str, bounty_id: str) -> Response:
        data = f"[\"{bounty_id}\"]"

        actions = {
            "description_action": "4ff0f897be640699fb1c7d16d9a515bbd30b87f9", 
            "meta_action": "9e0b8e9bcab138235158096c46ffd8cb0e168088"
        }

        next_router_state_tree = ["",{"children":["bounties",{"children":[["bountyId", bounty_id,"d"],{"children":["__PAGE__",{},f"/bounties/{bounty_id}","refresh"]}]}]},None,None,True]
        next_router_state_tree_as_string = json.dumps(next_router_state_tree)

        encoded_next_router_state_tree = urllib.parse.quote(next_router_state_tree_as_string)

        raw_response = ""
        for action in actions.values():
            headers = {
                "accept": "text/x-component",
                "accept-language": "en-US,en;q=0.9",
                "content-type": "text/plain;charset=UTF-8",
                "next-action": action,
                "next-router-state-tree": encoded_next_router_state_tree,
                "priority": "u=1, i",
                "sec-ch-ua": "\"Chromium\";v=\"130\", \"Microsoft Edge\";v=\"130\", \"Not?A_Brand\";v=\"99\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"Windows\"",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin"
            }

            response = requests.post(url, headers=headers, data=data, 
                         allow_redirects=True)

            raw_response += response.text

        return BaseResponse(raw_response)