from datetime import datetime
from responses.model_input import ModelInput
from responses.model_response import ModelResponse
from responses.request import Request, RequestResult
from responses.registry import ModelRegistry, DeploymentName
from responses.non_helm import non_helm_request
from typing import Optional
import logging
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import HTTPError, ConnectionError, Timeout
from typing import Any, Dict, Optional




HALLUCINATION_STRINGS = [
    "----------Message from assistant----------",
    "----------Message from system----------",
    "----------Message from agent",
]
RETRY_DELAY = 30
MAX_RETRIES = 3

class RequestHandler:
    def __init__(self, config):
        self.config = config
        self.logger = self._setup_logger()
        self.helm = config.get("helm", False)
        self.azure = config.get("azure", False)

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        log_file = os.path.join(self.config.get("log_dir", "."), "agent.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(message)s\n")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        return logger

    def remove_hallucinations(self, response: str) -> str:
        """Removes known hallucination patterns from the response."""
        for hallucination in HALLUCINATION_STRINGS:
            hallucination_index = response.find(hallucination)
            if hallucination_index != -1:
                response = response[:hallucination_index]
        return response.strip()

    @retry(
        stop=stop_after_attempt(30),
        wait=wait_exponential(multiplier=1, max=30),
        retry=retry_if_exception_type((HTTPError, ConnectionError, Timeout, http.client.RemoteDisconnected)),)
    def query(self, model_input: str, deployment_name: str, max_tokens: int = 1000, temperature: float = 1, stop_token: Optional[str] = "<STOP>") -> Dict[str, Any]:
        """
        A single function to call different models (e.g., HELM or non-HELM) based on the configuration.
        Wraps the model request with additional logic like logging, retries, and hallucination removal.
        """
        self.logger.info(f"Starting request for {deployment_name}")
        start_time = datetime.now()

        if self.helm:
            response = self._query_helm(model_input, deployment_name, max_tokens, temperature, stop_token)
        else:
            response = self._query_non_helm(model_input, deployment_name, max_tokens, temperature, stop_token)

        # End of the request, compute duration and clean up response
        end_time = datetime.now()
        request_duration = (end_time - start_time).total_seconds() * 1000

        cleaned_response = self.remove_hallucinations(response["full_response"])
        if "o1" not in deployment_name:
            cleaned_response += f"\n{stop_token}"

        num_response_tokens = self._get_num_tokens(cleaned_response)

        self.logger.info(f"Request successful. Time taken: {request_duration}ms, Tokens used: {num_response_tokens}")

        return {
            "value": cleaned_response,
            "full_response": response["full_response"],
            "time_taken_in_ms": request_duration,
            "num_tokens": num_response_tokens,
        }

    def _query_helm(self, model_input: str, deployment_name: str, max_tokens: int, temperature: float,
                    stop_token: Optional[str]) -> Dict[str, Any]:
        """Handles the request to HELM model."""
        
        model = ModelRegistry.get_model(deployment_name=DeploymentName.from_string(deployment_name))
        is_o1_model = "o1" in deployment_name  # Check if it's an o1 model

        request = Request(
            model=model,
            model_deployment=deployment_name,
            prompt=model_input,
            temperature=1 if is_o1_model else temperature,  # Fixed temperature for o1 models
            echo_prompt=False,
            max_tokens=max_tokens,
            stop_sequences=None if is_o1_model else [stop_token],  # No stop sequences for o1 models
        )

        try:
            request_result: RequestResult = self.crfm_service.make_request(auth=self.crfm_auth, request=request)
            response = request_result.completions[0].text
        except Exception as e:
            self.logger.error(f"HELM request failed for {deployment_name}: {e}")
            raise

        return {"full_response": response}


    def _query_non_helm(self, model_input: str, deployment_name: str, max_tokens: int, temperature: float, stop_token: Optional[str]) -> Dict[str, Any]:
        """Handles the request to non-HELM models (e.g., Azure)."""

        try:
            _, model_response = non_helm_request(
                model_name=deployment_name,
                input_message=model_input,
                temperature=temperature,
                max_tokens=max_tokens,
                stop_sequences=[stop_token],
                azure=self.azure,
            )
            response = model_response.full_response
        except Exception as e:
            self.logger.error(f"Non-HELM request failed for {deployment_name}: {e}")
            raise

        return {"full_response": response}


    def _handle_request_error(self, attempt: int, e: Exception) -> None:
        """Handles errors during the request process."""
        self.logger.error(f"Error during request: {str(e)}")
        if attempt < self.config.get("max_retries", 3) - 1:
            self.logger.info(f"Retrying request in {self.config.get('retry_delay', 5)} seconds...")
        else:
            raise RuntimeError(f"Request failed after {self.config.get('max_retries', 3)} attempts.") from e