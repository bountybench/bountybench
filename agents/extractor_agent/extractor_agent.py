from typing import List
from agents.base_agent import BaseAgent
from agents.extractor_agent.website_keywords import WEBSITE_KEYWORDS
from responses.response import Response


class ExtractorAgent(BaseAgent):

    def __init__(self, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.keywords = WEBSITE_KEYWORDS

    def run(self, responses: List[Response]) -> Response:
        if len(responses) != 1:
            raise Exception('Need exactly 1 response to start the agent and got {len(responses)} responses')
        response = responses[0]
        # TODO: Replace with the actual response object
        if issubclass(response.__class__, ScraperResponseInterface):
            return self.extract(response)
        else:
            raise Exception(
                f'Response not of an interpretable type. The response type is {response.__class__} but we expect a class of ScraperResponseInterface')