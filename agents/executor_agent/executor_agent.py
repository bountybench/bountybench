
class ExecuterAgent:
    def __init__(self, config):
        self.config = config

    # Standard agent function; every agent can be "run" on Responses, including no response. i.e. list can be empty. PlannerAgent... or should it still require metadata but perhaps there is no Response
    def run(self, responses: List[Response]) -> Response:
        if len(responses) != 1:
            return Exception(f'Accepts exactly a single response, you passed in {len(responses)} responses')
        response = responses[0]
        # Need to be careful with collissions of ResponseInterfaces, e.g. what if something both has a command and a plan. need to be sure it's specific enough. Maybe more specific/detail response types that have more specific mandates / requirements
        if issubclass(response.__class__, CommandResponseInterface):
            formulate_prompt_from_execution(response)
            self.execute_with_new_prompt()
        elif issubclass(response.__class__, PlanResponseInterface):
            formulate_prompt_from_plan(response)
            self.execute_with_new_prompt()
        else:
            raise Exception('Response not of an interpretable type. The response type is {response.__class__} but we expect a class of either Command or PlanResponseInterface')

    def execute_with_new_prompt(self):
        self.call_lm()
        self.parse_observation()
        self.execute_in_env()

    def formulate_prompt_from_plan(self, planner_response: PlannerResponse) -> str:
        """
        """
        prompt = combine_response_with_prompt(self.config.prompt, planner_response)
        self.prompt = prompt
        return prompt

    def formulate_prompt_from_execution(self, executor_response: ExecutorResponse) -> str:
        """
        """
        prompt = combine_response_with_prompt(self.config.prompt, executor_response)
        self.prompt = prompt
        return prompt
       
