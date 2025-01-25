import unittest
from pathlib import Path
from typing import List, Tuple
from unittest.mock import Mock, patch

from agents.base_agent import AgentConfig, BaseAgent
from messages.phase_messages.phase_message import PhaseMessage
from phases.base_phase import BasePhase
from workflows.base_workflow import BaseWorkflow


class MockAgent(BaseAgent):
    CONFIG_CLASS = AgentConfig


class TestPhase(BasePhase):
    def define_agents(self):
        return {}

    def define_resources(self):
        return {}

    def run_one_iteration(self, phase_message, agent_instance, previous_output):
        return Mock()

    def _initialize_agents(self):
        """Override to avoid agent initialization for testing"""
        pass


class TestWorkflow(BaseWorkflow):
    def _create_phases(self):
        phase1 = TestPhase(workflow=self)
        phase2 = TestPhase(workflow=self)
        phase3 = TestPhase(workflow=self)

        phase1 >> phase2 >> phase3
        self._register_root_phase(phase1)

    def _get_initial_prompt(self):
        return "test prompt"


class TestWorkflowGraph(unittest.TestCase):
    def setUp(self):
        self.workflow = TestWorkflow()

    def test_phase_graph_creation(self):
        phases = list(self.workflow._phase_graph.keys())
        self.assertEqual(len(phases), 3)
        self.assertEqual(self.workflow._root_phase, phases[0])

        # Test connections
        self.assertEqual(len(self.workflow._phase_graph[phases[0]]), 1)
        self.assertEqual(self.workflow._phase_graph[phases[0]][0], phases[1])
        self.assertEqual(self.workflow._phase_graph[phases[1]][0], phases[2])

    def test_missing_root_phase(self):
        workflow = TestWorkflow(task_dir=Path("/tmp"), bounty_number="123")
        workflow._root_phase = None

        with self.assertRaises(ValueError):
            list(workflow._run_phases())

    def test_phase_failure(self):
        with patch("phases.base_phase.BasePhase.run_phase") as mock_run:
            mock_message = PhaseMessage(agent_messages=[])
            mock_run.return_value = mock_message

            self.workflow.run()
            self.assertEqual(self.workflow.status.value, "completed_failure")


if __name__ == "__main__":
    unittest.main()
