from abc import ABC
from typing import Optional
from resources.resource_manager import ResourceManager

# ResourceManager is a global construct that any agent or anyone can access you just create it at startup time for python environment 


class BaseWorkflow(ABC):
    def __init__():
        self.resource_manager = ResourceManager()
    
    @method
    def run_agent(self, agent: BaseAgent, responses: List[Response]) -> Response responses:
        return agent.run(self.resource_manager, responses)


    @abstract_method
    def run(self)
        pass


w = SimpleExecutorWorkflow(args)
w.run()

class SimpleExecutorWorkflow(BaseWorkflow):
    def __init__():
        super.__init__() # doulbe check synta

    
    def run():
        args = parse_args()
        agent = SimpleExecutionAgent(response_history=3, max_input_tokens=...)
        response = self.run_agent(agent, [])
        for i in range(args.num_iterations):
            response = self.run_agent(agent, [response])
            if issubclass(response.__class__, AnswerResponseInterface):
                print(check_response_answer(response))
                break


