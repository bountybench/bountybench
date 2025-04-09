import os
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from time import sleep
from typing import List

from dotenv import find_dotenv, load_dotenv

from resources.model_resource.model_response import ModelResponse
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


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
        env_path = Path(find_dotenv())

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

    def make_request(
        self,
        model: str,
        message: str,
        temperature: float,
        max_tokens: int,
        stop_sequences: List[str],
        logging_interval: float = 5.0,
        timeout: float = 300.0,
    ) -> ModelResponse:
        """
        A method that:
            - Spawns a thread to run the request method.
            - Logs a message while waiting for the request to finish.
            - Returns the ModelResponse once the thread is done.
        """
        start_time = time.time()

        done_flag = [False]  # Shared boolean to signal completion
        response_holder = [None]  # Holds the ModelResponse when done
        error_holder = [None]  # Holds exception info if something goes wrong

        def run_request():
            try:
                response = self.request(
                    model, message, temperature, max_tokens, stop_sequences
                )
                response_holder[0] = response
            except Exception as e:
                error_holder[0] = e
            finally:
                done_flag[0] = True

        # Start the child-class _request logic in a separate thread
        request_thread = threading.Thread(target=run_request)
        request_thread.start()

        # Periodically log heartbeat until request completes or fails
        while not done_flag[0]:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.warning(f"Timeout of {timeout}s reached. Cancelling request.")
                raise TimeoutError(f"Model request timed out after {timeout} seconds")
            logger.info(
                f"{elapsed:.1f}s has passed. Still waiting for LLM provider to respond..."
            )
            sleep(logging_interval)

        # If the child thread encountered an error, re-raise it
        if error_holder[0] is not None:
            exception = error_holder[0]
            # Log the status code if available
            if hasattr(exception, "status_code"):
                logger.error(f"API error with status code: {exception.status_code}")
            raise exception

        # Otherwise, return the response from the child
        return response_holder[0]

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

    @abstractmethod
    def get_num_tokens(self, model: str, message: str) -> int:
        """
        Abstract method to get the number of tokens for a given message.
        Args:
            model (str): The model to use.
            message (str): The message for which to count tokens.
        Returns:
            int: The number of tokens in the message.
        """
        pass
