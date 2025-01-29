import unittest
from unittest.mock import patch

from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.executor_agent_message import ExecutorAgentMessage
from messages.agent_messages.exploit_agent_message import ExploitAgentMessage
from messages.agent_messages.patch_agent_message import PatchAgentMessage
from resources.utils import run_command

@patch("messages.message_utils.log_message")
class TestAgentMessageClasses(unittest.TestCase):
    pass