import logging

from agents.dataclasses.agent_spec import AgentConfig
from agents.simple_agent.simple_agent import SimpleExecutionAgent
from responses.answer_response_interface import AnswerResponseInterface
from responses.response import Response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent: SimpleExecutionAgent

agent_config: AgentConfig = AgentConfig(
    model='openai/gpt-4o-2024-05-13',
    max_output_tokens=2000,
    max_input_tokens=6000,
    max_iterations=15,
    max_response_len=3,
    helm=True
)

agent = SimpleExecutionAgent(agent_config)


def check_response_answer(response: AnswerResponseInterface, answer: str) -> None:
    if response.answer == answer:
        logger.info("Correct answer!")
    else:
        logger.info(
            f"Wrong answer! Expected: {answer}, Got: {response.answer}")


def simple_workflow(answer: str):
    response: Response = agent.run()
    for _ in range(agent_config.max_iterations):
        response = agent.run(response)
        if issubclass(response.__class__, AnswerResponseInterface):
            check_response_answer(response, answer)
            break
