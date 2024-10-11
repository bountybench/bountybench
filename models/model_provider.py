import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from models.model_response import ModelResponse


class ModelProvider(ABC):
    """
    Abstract Base Class for model providers. Provides a general interface for creating a client, making requests, tokenizing, decoding tokens, and getting the number of tokens for a specific model.
    """

    @classmethod
    def _api_key(cls) -> str:
        """
        Retrieve the API key from environment variables or a .env file.
        If the API key is not found, raises a ValueError with an appropriate message.
        Returns:
            str: The API key for the model provider.
        """
        if cls.__name__ == "AzureOpenAIModels":
            env_var = "AZURE_OPENAI_API_KEY"
        else:
            env_var = f"{cls.__name__.upper().replace('MODELS', '')}_API_KEY"

        # Define the path to the .env file, which is assumed to be in the root directory.
        env_path = Path(__file__).resolve().parent.parent / ".env"

        # If the .env file exists, load environment variables from it.
        if env_path.is_file():
            load_dotenv(dotenv_path=env_path)

        # Retrieve the API key from the environment.
        key = os.getenv(env_var)

        # Raise an error if the API key is not set in the environment or .env file.
        if not key:
            if env_path.is_file():
                raise ValueError(
                    f"{env_var} is not set in the .env file or environment variables"
                )
            else:
                raise ValueError(
                    f"{env_var} is not set in environment variables and .env file not found at {env_path}"
                )
        return key

    @abstractmethod
    def create_client(self):
        """
        Abstract method to create a client for the model provider.
        Each subclass should implement the logic to instantiate the specific client.
        """
        pass

    @abstractmethod
    def request(
        self,
        model: str,
        message: str,
        temperature: float,
        max_tokens: int,
        stop_sequences: List[str],
    ) -> ModelResponse:
        """
        Abstract method to request a response from a model.
        Args:
            model (str): The model to use for the request.
            message (str): The input message to be sent to the model.
            temperature (float): Controls the creativity of the response.
            max_tokens (int): The maximum number of tokens in the response.
            stop_sequences (List[str]): Sequences that will stop the model's response.
        """
        pass

    @abstractmethod
    def tokenize(self, model: str, message: str) -> List[int]:
        """
        Abstract method to tokenize a given message for a specific model.
        Args:
            model (str): The model to use for tokenization.
            message (str): The message to tokenize.
        Returns:
            List[int]: A list of token IDs corresponding to the input message.
        """
        pass

    @abstractmethod
    def decode(self, model: str, tokens: List[int]) -> str:
        """
        Abstract method to decode tokens back into a string.
        Args:
            model (str): The model to use for decoding.
            tokens (List[int]): A list of token IDs to decode.
        Returns:
            str: The decoded string.
        """
        pass
