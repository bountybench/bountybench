import unittest
from unittest.mock import Mock
from agents.executor_agent.executor_agent import ExecutorAgent, ExecutorAgentConfig
from messages.action_messages.command_message import CommandMessage
from messages.agent_messages.executor_agent_message import ExecutorAgentMessage

class TestAsyncExecutorAgent(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Initialize the agent
        self.agent = ExecutorAgent('executor_agent', agent_config=ExecutorAgentConfig())

    async def test_run_with_valid_message_type(self):
        """
        Test run() returns valid message. 
        Need to run this in AsyncioTestCase due to async.
        """

        command_message = CommandMessage("test_id", "command: ls")
        self.agent.execute = Mock(return_value=command_message)

        await self.agent.run(messages=[command_message])

        # Check if execute() was called
        self.agent.execute.assert_called_once()


# class TestExecutorAgent(unittest.TestCase):

#     def setUp(self):
#         # Initialize the agent
#         self.agent = ExecutorAgent('executor_agent', agent_config=ExecutorAgentConfig())

#     def test_execute_calls_lm_and_runs_command(self):
#         """
#         Tests that execute() calls the LM and executes command.
#         """
#         # Simulate the call to call_lm
#         self.agent.call_lm = Mock(return_value=CommandMessage("command: pwd"))

#         # Simulate kali env that just returns the command it was given
#         self.agent.kali_env = Mock()
#         self.agent.kali_env.run_command = lambda command, *args, **kwargs: (command, '')

#         result = self.agent.execute()

#         # check that command was properly passed into env
#         self.assertEqual(result.observation.raw_output, "pwd")

if __name__ == "__main__":
    unittest.main()