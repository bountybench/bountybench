from typing import List

from agents.base_agent import BaseAgent
from agents.extractor_agent.extractor_prompt import EXTRACTOR_PROMPT
from agents.extractor_agent.website_keywords import WEBSITE_KEYWORDS
from models.model_response import ModelResponse
from models.query import query
from responses.extraction_response import ExtractionResponse
from responses.response import Response
from utils.logger import get_main_logger

logger = get_main_logger(__name__)

MAX_RETRIES = 3
TEMPERATURE = 0.5


class ExtractorAgent(BaseAgent):

    def __init__(self, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.keywords = WEBSITE_KEYWORDS
        self.prompt = EXTRACTOR_PROMPT

    def run(self, responses: List[Response]) -> Response:
        if len(responses) != 1:
            raise Exception(
                'Need exactly 1 response to start the agent and got {len(responses)} responses')
        response = responses[0]
        # TODO: Replace with the actual response object
        if issubclass(response.__class__, ScraperResponseInterface):
            return self.extract(response)
        else:
            raise Exception(
                f'Response not of an interpretable type. The response type is {response.__class__} but we expect a class of ScraperResponseInterface')

    def extract(self, scraper_response: ScraperResponse) -> ExtractionResponse:
        """
        Extracts the relevant information from the website
        """
        extractor = self.generate_extractor(scraper_response)

        return extractor(scraper_response)

    def generate_extractor(self, scraper_response: ScraperResponse) -> callable:
        """
        Generates the extractor function based on the scraper response
        """
        model_input = self.prompt.format(scraper_response.response)
        while iterations < MAX_RETRIES:
            model_response: ModelResponse = query(
                model=self.config.model,
                message=model_input,
                temperature=TEMPERATURE,
                max_tokens=self.config.max_output_tokens,
                stop_sequences=[],
                helm=self.config.use_helm
            )

            model_response = model_response.content

            try:
                return self.create_function_from_string(model_response)
            except Exception as e:
                logger.warning(
                    f"Retrying {iterations}/{MAX_RETRIES} after error: {e}")
                iterations += 1

    def create_function_from_string(function_string: str) -> callable:
        """
        Takes a string containing a function definition and returns a callable function.

        Args:
            function_string: String containing the function definition

        Returns:
            A callable function object
        """
        # Create a new namespace dictionary
        namespace = {}

        try:
            # Execute the function string in the new namespace
            exec(function_string, namespace)

            # Get the function name from the namespace
            # This assumes there's only one function defined in the string
            function_name = [
                name for name in namespace if callable(namespace[name])][0]

            # Return the callable function
            return namespace[function_name]
        except Exception as e:
            raise Exception(f"Failed to create function from string: {str(e)}")
