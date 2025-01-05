from typing import Any, Dict, List

from agents.base_agent import BaseAgent
from agents.extractor_agent.extractor_prompt import EXTRACTOR_PROMPT
from agents.extractor_agent.website_keywords import WEBSITE_KEYWORDS
from models.model_response import ModelResponse
from models.query import query
from messages.extraction_message import ExtractionMessage
from messages.message import Message
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

    def run(self, messages: List[Message]) -> Message:
        if len(messages) != 1:
            raise Exception(
                'Need exactly 1 message to start the agent and got {len(messages)} messages')
        message = messages[0]
        # TODO: Replace with the actual message object
        if issubclass(message.__class__, ScraperMessageInterface):
            return self._extract(message)
        else:
            raise Exception(
                f'Message not of an interpretable type. The message type is {message.__class__} but we expect a class of ScraperMessageInterface')

    def _extract(self, scraper_message: ScraperMessage) -> ExtractionMessage:
        """
        Extracts the relevant information from the website
        """
        iterations = 0
        while iterations < MAX_RETRIES:
            try:
                extractor = self._generate_extractor(scraper_message)
                extraction = extractor(scraper_message.message)
                extraction['message'] = scraper_message.message
                extraction['link'] = scraper_message.link
                return self._parse_extraction(extraction)
            except Exception as e:
                logger.error(f"Failed to extract information: {str(e)}")
                iterations += 1

        return extractor(scraper_message)

    def _generate_extractor(self, scraper_message: ScraperMessage) -> callable:
        """
        Generates the extractor function based on the scraper message
        """
        model_input = self.prompt.format(scraper_message.message)
        model_message: ModelMessage = query(
            model=self.config.model,
            message=model_input,
            temperature=TEMPERATURE,
            max_tokens=self.config.max_output_tokens,
            stop_sequences=[],
            helm=self.config.use_helm
        )

        model_message = model_message.content

        try:
            return self._create_function_from_string(model_message)
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
    
    def _parse_extraction(self, extraction: Dict[str, Any]) -> ExtractionMessage:
        """
        Parses the extraction dictionary into an ExtractionMessage object.

        Args:
            extraction (Dict[str, Any]): The extraction data.

        Returns:
            ExtractionMessage: The parsed extraction message.

        Raises:
            TypeError: If extraction is not a dictionary.
            ExtractionParsingError: If required fields are missing or invalid.
        """
        if not isinstance(extraction, dict):
            raise TypeError("Extraction must be a dictionary.")

        required_fields = ['message', 'description', 'proof', 'bug_commit', 'bug_tag', 'patch_commit', 'patch_tag', 'extra', 'link']
        missing_fields = [field for field in required_fields if field not in extraction]
        if missing_fields:
            raise ValueError(
                f"Extraction is missing required fields: {', '.join(missing_fields)}"
            )

        
        message = extraction['message']
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

        return ExtractionMessage(
            message=message,
            description=description,
            proof=proof,
            bug_commit=bug_commit,
            bug_tag=bug_tag,
            patch_commit=patch_commit,
            patch_tag=patch_tag,
            metadata=metadata,
            link=link,
        )