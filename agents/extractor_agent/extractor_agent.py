from typing import Any, Dict, List

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
            return self._extract(response)
        else:
            raise Exception(
                f'Response not of an interpretable type. The response type is {response.__class__} but we expect a class of ScraperResponseInterface')

    def _extract(self, scraper_response: ScraperResponse) -> ExtractionResponse:
        """
        Extracts the relevant information from the website
        """
        iterations = 0
        while iterations < MAX_RETRIES:
            try:
                extractor = self._generate_extractor(scraper_response)
                extraction = extractor(scraper_response.response)
                extraction['response'] = scraper_response.response
                extraction['link'] = scraper_response.link
                return self._parse_extraction(extraction)
            except Exception as e:
                logger.error(f"Failed to extract information: {str(e)}")
                iterations += 1

        return extractor(scraper_response)

    def _generate_extractor(self, scraper_response: ScraperResponse) -> callable:
        """
        Generates the extractor function based on the scraper response
        """
        model_input = self.prompt.format(scraper_response.response)
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
            return self._create_function_from_string(model_response)
        except Exception as e:
           raise Exception(f"Failed to generate extractor function: {str(e)}")

    def _create_function_from_string(self, function_string: str) -> callable:
        """
        Takes a string containing a function definition and returns a callable function.

        Args:
            function_string: String containing the function definition

        Returns:
            A callable function object
        """
        # Create a new namespace dictionary
        namespace = {}

        exec(function_string, namespace)

        # Get the function name from the namespace
        # This assumes there's only one function defined in the string
        function_name = [
            name for name in namespace if callable(namespace[name])][0]

        # Return the callable function
        return namespace[function_name]
    
    def _parse_extraction(self, extraction: Dict[str, Any]) -> ExtractionResponse:
        """
        Parses the extraction dictionary into an ExtractionResponse object.

        Args:
            extraction (Dict[str, Any]): The extraction data.

        Returns:
            ExtractionResponse: The parsed extraction response.

        Raises:
            TypeError: If extraction is not a dictionary.
            ExtractionParsingError: If required fields are missing or invalid.
        """
        if not isinstance(extraction, dict):
            raise TypeError("Extraction must be a dictionary.")

        required_fields = ['response', 'description', 'proof', 'bug_commit', 'bug_tag', 'patch_commit', 'patch_tag', 'extra', 'link']
        missing_fields = [field for field in required_fields if field not in extraction]
        if missing_fields:
            raise ValueError(
                f"Extraction is missing required fields: {', '.join(missing_fields)}"
            )

        
        response = extraction['response']
        description = extraction['description']
        proof = extraction['proof']
        bug_commit = extraction['bug_commit']
        bug_tag = extraction['bug_tag']
        patch_commit = extraction['patch_commit']
        patch_tag = extraction['patch_tag']
        metadata = extraction['extra']
        link = extraction['link']

        # Example type checks (optional)
        if not isinstance(description, str):
            raise TypeError("description must be a string.")
        if not isinstance(proof, str):
            raise TypeError("proof must be a string.")
        if not isinstance(bug_commit, str):
            raise TypeError("bug_commit must be a string.")
        if not isinstance(bug_tag, str):
            raise TypeError("bug_tag must be a string.")
        if not isinstance(patch_commit, str):
            raise TypeError("patch_commit must be a string.")
        if not isinstance(patch_tag, str):
            raise TypeError("patch_tag must be a string.")
        if not isinstance(metadata, dict):
            raise TypeError("extra must be a dictionary.")

        return ExtractionResponse(
            response=response,
            description=description,
            proof=proof,
            bug_commit=bug_commit,
            bug_tag=bug_tag,
            patch_commit=patch_commit,
            patch_tag=patch_tag,
            metadata=metadata,
            link=link,
        )