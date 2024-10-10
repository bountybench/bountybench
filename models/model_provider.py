import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List

from dotenv import load_dotenv


class ModelProvider(ABC):
    @classmethod
    def _api_key(cls) -> str:
        if cls.__name__ == "AzureOpenAIModels":
            env_var = "AZURE_OPENAI_API_KEY"
        else:
            env_var = f"{cls.__name__.upper().replace('MODELS', '')}_API_KEY"
        current_dir = Path(__file__).resolve().parent.parent
        root_dir = current_dir.parent
        env_path = root_dir / ".env"
        if env_path.is_file():
            load_dotenv(dotenv_path=env_path)
        key = os.getenv(env_var)
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
        pass

    @abstractmethod
    def request(
        self,
        model: str,
        message: str,
        temperature: float,
        max_tokens: int,
        stop_sequences: List[str],
    ):
        pass

    @abstractmethod
    def tokenize(self, model: str, message: str):
        pass

    @abstractmethod
    def decode_tokens(self, model: str, tokens: List[int]) -> str:
        pass

    @abstractmethod
    def get_num_tokens(self, model: str, message: str) -> int:
        pass
