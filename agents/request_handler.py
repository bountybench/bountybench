from datetime import datetime
from responses.model_input import ModelInput
from responses.model_response import ModelResponse
from responses.request import Request, RequestResult
from responses.registry import ModelRegistry, DeploymentName
from responses.non_helm import non_helm_request
from typing import Optional


HALLUCINATION_STRINGS = [
    "----------Message from assistant----------",
    "----------Message from system----------",
    "----------Message from agent",
]

class RequestHandler:
    def __init__(self, config):
        self.config = config
        self.helm = config.get("helm", False)
        self.azure = config.get("azure", False)
        self.logger = self._setup_logger()

    def _setup_logger(self):
        import logging
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        logger.addHandler(handler)
        return logger

    def make_any_lm_request(self, model_input: ModelInput) -> ModelResponse:
        """
        Main method to handle the request. It delegates to the appropriate handler (HELM, or non-HELM).
        """
        if self.helm:
            return self._handle_helm_request(model_input)

        return self._handle_non_helm_request(model_input)

    def _handle_helm_request(self, model_input: ModelInput) -> ModelResponse:
        """
        Sends a request to the HELM model and returns the processed response.
        """
        self.logger.info("Making request to HELM")
        start_time = datetime.now()

        request = self._build_helm_request(model_input)

        request_result: RequestResult = self._make_helm_request(request)
        response = request_result.completions[0].text

        return self._process_model_response(response, start_time)

    def _build_helm_request(self, model_input: ModelInput) -> Request:
        """
        Constructs the HELM request based on model deployment and input.
        """
        deployment_name = self.config.get("deployment_name")
        max_tokens = self.config.get("max_tokens", 1000)
        stop_token = self.config.get("stop_token", "<STOP>")
        temperature = 1 if "o1" in deployment_name else self.config.get("temperature", 0.7)

        return Request(
            model=ModelRegistry.get_model(
                deployment_name=DeploymentName.from_string(deployment_name)
            ),
            model_deployment=deployment_name,
            prompt=model_input.value,
            temperature=temperature,
            echo_prompt=False,
            max_tokens=max_tokens,
            stop_sequences=[stop_token],
        )

    def _handle_non_helm_request(self, model_input: ModelInput) -> ModelResponse:
        """
        Sends a request to a non-HELM model (e.g., Azure) and returns the processed response.
        """
        self.logger.info("Making request to non-HELM model")
        _, model_response = non_helm_request(
            model_name=self.config["deployment_name"],
            input_message=model_input.value,
            temperature=self.config.get("temperature", 0.7),
            max_tokens=self.config.get("max_tokens", 1000),
            stop_sequences=[self.config.get("stop_token", "<STOP>")],
            azure=self.azure,
        )

        return self._process_model_response(model_response.full_response)

    def _process_model_response(self, response: str, start_time: Optional[datetime] = None) -> ModelResponse:
        """
        Processes the raw model response, removes hallucinations, and calculates metadata.
        """
        cleaned_response = self.remove_hallucinations(response) + f"\n{self.config.get('stop_token', '<STOP>')}"
        time_taken_ms = (datetime.now() - start_time).total_seconds() * 1000 if start_time else 0
        num_tokens = self._get_num_tokens(cleaned_response)

        return ModelResponse(
            value=cleaned_response,
            full_response=response,
            time_taken_in_ms=time_taken_ms,
            num_tokens=num_tokens,
        )

    def _make_helm_request(self, request: Request) -> RequestResult:
        """
        Makes the actual request to the HELM service. This can be mocked or real.
        """
        return self.crfm_service.make_request(auth=self.crfm_auth, request=request)

    def _get_num_tokens(self, response: str) -> int:
        """
        Counts the number of tokens in the response.
        """
        return len(response.split())  # Replace with actual tokenization logic

    def remove_hallucinations(self, response: str) -> str:
        """
        Removes known hallucination patterns from the response.
        """

        for hallucination in HALLUCINATION_STRINGS:
            hallucination_index = response.find(hallucination)
            if hallucination_index != -1:
                response = response[:hallucination_index]
        return response.strip()