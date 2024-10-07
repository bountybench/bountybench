from agent import BaseAgent

class SimpleExecutionAgent(BaseAgent):
    def __init__(self, config):
        self.config = config
        self.max_response_len = 3
        self.memory = []

    def run(self, responses: List[Response]) -> Response:
        if len(responses) > 1:
            return Exception(f'Accepts at most a single response, you passed in {len(responses)} responses')
        if not response:
            self.execute()
        response = responses[0]
        if issubclass(response.__class__, ExecutorResponseInterface):
            self.formulate_prompt(response)
            return self.execute()
        else:
            raise Exception('Response not of an interpretable type. The response type is {response.__class__} but we expect a class of CommandResponseInterface')

    def execute(self):
        lm_response = self.call_lm()
        observation = self.execute_in_env(lm_response)
        return format_response(lm_response, observation)

    def formulate_prompt(self, executor_response: ExecutorResponse) -> str:
        """
        """
        if len(self.memory) >= self.max_response_len:
            self.memory = self.memory[1:] + executor_response 
        prompt = INITIAL_PROMPT + self.memory
        self.prompt = prompt
        return prompt
    
    def call_lm(self):
        model_input = self.prompt
        return self._handle_request(model_input)

    
