import unittest
from unittest.mock import MagicMock, patch
from typing import List, Optional, Tuple

from phases.base_phase import BasePhase, PhaseConfig
from agents.base_agent import BaseAgent
from messages.message import Message
from messages.answer_message import AnswerMessage, AnswerMessageInterface
from utils import workflow_logger
from utils.logger import get_main_logger

logger = get_main_logger(__name__)


class SampleAgent(BaseAgent):
    def __init__(self, name: str, magic_iteration: int = -1):
        super().__init__()
        self.name = name
        self.magic_iteration = magic_iteration
        self.run_count = 0

    def run(self, messages: List[Message]) -> Message:
        self.run_count += 1
        if self.magic_iteration >= 0 and self.run_count == self.magic_iteration:
            return AnswerMessage("answer: Magic done")
        return Message("Regular message")


class SamplePhase(BasePhase):
    def run_one_iteration(
        self,
        agent_instance: BaseAgent,
        previous_output: Optional[Message],
        iteration_num: int,
    ) -> Tuple[Message, bool]:
        input_list = []
        if previous_output:
            input_list.append(previous_output)

        message = agent_instance.run(input_list)

        if isinstance(message, AnswerMessageInterface):
            logger.info("SamplePhase success condition met!")
            self._set_phase_summary("completed_success")
            return message, True

        return message, False


class FakeAgentA(BaseAgent):
    def run(self, messages: List[Message]) -> Message:
        return Message("FakeAgentA")


class FakeAgentB(BaseAgent):
    def run(self, messages: List[Message]) -> Message:
        return Message("FakeAgentB")


class PhaseWithRequiredAgents(BasePhase):
    REQUIRED_AGENTS = [FakeAgentA, FakeAgentB]

    def run_one_iteration(
        self,
        agent_instance: BaseAgent,
        previous_output: Optional[Message],
        iteration_num: int,
    ) -> Tuple[Message, bool]:
        resp = agent_instance.run([])
        return resp, False


class TestBasePhase(unittest.TestCase):
    @patch("phases.base_phase.workflow_logger")
    def test_base_phase_runs_all_iterations(self, mock_logger):
        mock_logger.phase = MagicMock()
        mock_logger.phase.return_value.__enter__.return_value = mock_logger
        mock_logger.phase.return_value.__exit__.return_value = False

        agent1 = SampleAgent("Agent1", magic_iteration=-1)
        agent2 = SampleAgent("Agent2", magic_iteration=-1)
        config = PhaseConfig(
            phase_number=1,
            phase_name="Sample",
            max_iterations=5,
            agents=[("Agent1", agent1), ("Agent2", agent2)],
        )

        phase = SamplePhase(phase_config=config)
        final_message, success_flag = phase.run_phase()

        self.assertFalse(success_flag)
        self.assertEqual(agent1.run_count, 3)
        self.assertEqual(agent2.run_count, 2)
        self.assertEqual(final_message.message, "Regular message")

        mock_logger.phase.assert_called_with(phase)

    @patch("phases.base_phase.workflow_logger")
    def test_base_phase_stops_early(self, mock_logger):
        mock_logger.phase = MagicMock()
        mock_logger.phase.return_value.__enter__.return_value = mock_logger
        mock_logger.phase.return_value.__exit__.return_value = False

        agent1 = SampleAgent("Agent1", magic_iteration=-1)
        agent2 = SampleAgent("Agent2", magic_iteration=1)
        config = PhaseConfig(
            phase_number=2,
            phase_name="Exploit",
            max_iterations=5,
            agents=[("Agent1", agent1), ("Agent2", agent2)],
        )

        phase = SamplePhase(phase_config=config)
        final_message, success_flag = phase.run_phase()

        self.assertEqual(agent1.run_count, 1)
        self.assertEqual(agent2.run_count, 1)
        self.assertTrue(success_flag)
        self.assertIsInstance(final_message, AnswerMessageInterface)

        self.assertEqual(phase.phase_summary, "completed_success")

    @patch("phases.base_phase.workflow_logger")
    def test_base_phase_with_initial_message(self, mock_logger):
        mock_logger.phase = MagicMock()
        mock_logger.phase.return_value.__enter__.return_value = mock_logger
        mock_logger.phase.return_value.__exit__.return_value = False

        agent = SampleAgent("Agent1", magic_iteration=-1)
        config = PhaseConfig(
            phase_number=3,
            phase_name="TestInitMessage",
            max_iterations=3,
            agents=[("Agent1", agent)],
        )

        initial_resp = Message("Initial")
        phase = SamplePhase(phase_config=config, initial_message=initial_resp)
        final_message, success_flag = phase.run_phase()

        self.assertEqual(agent.run_count, 3)
        self.assertFalse(success_flag)
        self.assertEqual(final_message.message, "Regular message")

    @patch("phases.base_phase.workflow_logger")
    def test_required_agents_success(self, mock_logger):
        agent_a = FakeAgentA()
        agent_b = FakeAgentB()
        config = PhaseConfig(
            phase_number=10,
            phase_name="WithRequired",
            max_iterations=2,
            agents=[
                ("A", agent_a),
                ("B", agent_b),
            ],
        )
        phase = PhaseWithRequiredAgents(phase_config=config)
        final_message, success_flag = phase.run_phase()

        self.assertFalse(success_flag)
        self.assertEqual(final_message.message, "FakeAgentB")

    @patch("phases.base_phase.workflow_logger")
    def test_required_agents_missing(self, mock_logger):
        agent_a = FakeAgentA()
        config = PhaseConfig(
            phase_number=11,
            phase_name="MissingAgent",
            max_iterations=2,
            agents=[
                ("A", agent_a),
            ],
        )
        with self.assertRaises(ValueError) as context:
            _ = PhaseWithRequiredAgents(phase_config=config)

        self.assertIn("requires an agent of type FakeAgentB", str(context.exception))


if __name__ == "__main__":
    unittest.main()
