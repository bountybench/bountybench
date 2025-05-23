from functools import partial
from unittest.mock import Mock, patch

import pytest

from messages.action_messages.action_message import ActionMessage
from messages.agent_messages.agent_message import AgentMessage
from messages.phase_messages.phase_message import PhaseMessage
from messages.workflow_message import WorkflowMessage
from resources.memory_resource.memory_function import MemoryTruncationFunctions
from resources.memory_resource.memory_prompt import MemoryPrompts
from resources.memory_resource.memory_resource import (
    MemoryResource,
    MemoryResourceConfig,
)


@pytest.fixture(scope="session", autouse=True)
def patcher():
    logger_patcher = patch("utils.logger.get_main_logger", return_value=Mock())
    workflow_patcher = patch.object(WorkflowMessage, "save", return_value=None)

    logger_patcher.start()
    workflow_patcher.start()

    yield

    logger_patcher.stop()
    workflow_patcher.stop()


@pytest.fixture
def message_tree():
    workflow_message = WorkflowMessage("")
    prev_phase = None

    last_action_message = None
    last_agent_message = None
    last_phase_message = None

    for i in range(2):
        phase_id = f"phase_{i}"
        phase_message = PhaseMessage(phase_id=phase_id, prev=prev_phase)
        prev_phase = phase_message

        initial_prompt = AgentMessage("system", "initial prompt")
        phase_message.add_child_message(initial_prompt)

        prev_agent = initial_prompt
        for j in range(2):
            agent_id = f"phase_{i}_agent_{j}"
            agent_message = AgentMessage(agent_id=agent_id, prev=prev_agent)
            prev_agent = agent_message

            action_id = action_message = "action"
            action_message = ActionMessage(
                resource_id=action_id, message=action_message
            )

            agent_message.add_child_message(action_message)
            phase_message.add_child_message(agent_message)

        last_action_message = action_message
        last_agent_message = agent_message

        workflow_message.add_child_message(phase_message)

    last_phase_message = phase_message

    config = MemoryResourceConfig(
        fmt="{prev_phase_messages}!!{prev_agent_messages}!!{prev_action_messages}",
        collate_fn=lambda x, start=0: " ".join(x),
        segment_trunc_fn=MemoryTruncationFunctions.segment_fn_noop,
        memory_trunc_fn=MemoryTruncationFunctions.memory_fn_noop,
    )

    mem_resource = MemoryResource("memory", config)

    return (
        last_action_message,
        last_agent_message,
        last_phase_message,
        config,
        mem_resource,
    )


def test_get_memory_from_last_phase_message(message_tree):
    """
    Given the latest phase message (phase_1), reconstruct memory.
    The memory should only contain previous phase messages (phase_0*),
    but current phase past agent or action messages should be N/A.
    """
    (
        last_action_message,
        last_agent_message,
        last_phase_message,
        config,
        mem_resource,
    ) = message_tree

    memory = mem_resource.get_memory(last_phase_message).memory
    memory_without_prompt = memory.replace("initial prompt\n\n", "")

    expected_prev_phases = [
        "[phase_0_agent_0] ",
        "[phase_0_agent_1] ",
    ]

    expected_memory = (
        MemoryPrompts._DEFAULT_SEGUE + "\n" + " ".join(expected_prev_phases)
    )

    assert memory_without_prompt == expected_memory


def test_get_memory_from_last_agent_message(message_tree):
    """
    Given the latest agent message (phase_1, agent_1), reconstruct memory.
    The memory should contain previous phase messages (phase_0*)
    as well as previous agent messages in current phase (phase_1_agent*)
    but current agent, past action messages should be N/A.

    Note that the latest agent message (phase_1, agent_1) is added to the
    prev_agents_memory.
    """
    (
        last_action_message,
        last_agent_message,
        last_phase_message,
        config,
        mem_resource,
    ) = message_tree

    memory = mem_resource.get_memory(last_agent_message).memory
    memory_without_prompt = memory.replace("initial prompt\n\n", "")

    expected_prev_phases = [
        "[phase_0_agent_0] ",
        "[phase_0_agent_1] ",
    ]
    expected_prev_agents = [
        "[phase_1_agent_0] ",
    ]
    expected_memory = (
        f"{MemoryPrompts._DEFAULT_SEGUE}\n"
        f"{' '.join(expected_prev_phases)}\n"
        f"{' '.join(expected_prev_agents)}"
    )

    assert memory_without_prompt == expected_memory


def test_get_memory_from_last_action_message(message_tree):
    """
    Given the latest action message (phase_1, agent_1, action), reconstruct memory.
    The memory should contain previous phase messages (phase_0_*)
    as well as previous agent messages in current phase (phase_1_agent_0*)
    and current agent, past action messages (phase_1_agent_1*)

    Note that here, phase_1_agent_1 is in prev_actions memory.
    """
    (
        last_action_message,
        last_agent_message,
        last_phase_message,
        config,
        mem_resource,
    ) = message_tree

    memory = mem_resource.get_memory(last_action_message).memory
    memory_without_prompt = memory.replace("initial prompt\n\n", "")

    expected_prev_phases = [
        "[phase_0_agent_0] ",
        "[phase_0_agent_1] ",
    ]
    expected_prev_agents = [
        "[phase_1_agent_0] ",
    ]
    expected_prev_actions = ["[phase_1_agent_1]  [phase_1_agent_1/action] action"]

    expected_memory = (
        f"{MemoryPrompts._DEFAULT_SEGUE}\n"
        f"{' '.join(expected_prev_phases)}\n"
        f"{' '.join(expected_prev_agents)}\n"
        f"{' '.join(expected_prev_actions)}"
    )

    assert memory_without_prompt == expected_memory


def test_config_validation():
    """
    Check that erroneous configurations are properly flagged.
    """
    # Workflow scope should include other messages
    faulty_fmt_lacking_kwargs = "{prev_agent_messages}"
    # Format string should include a defined set of kwargs
    faulty_fmt_bad_kwargs = "{random_kwarg}"

    # Collate function should convert list of messages to string
    faulty_collate_fn = lambda x: x

    checks = {
        "fmt": faulty_fmt_lacking_kwargs,
        "fmt": faulty_fmt_bad_kwargs,
        "collate_fn": faulty_collate_fn,
    }

    for kw, check in checks.items():
        with pytest.raises((AssertionError, ValueError)):
            _ = MemoryResourceConfig(**{kw: check})


def test_segment_truncation_by_message(message_tree):
    """
    Check that each segment is truncated except for the very last input.
    """
    (
        last_action_message,
        last_agent_message,
        last_phase_message,
        config,
        mem_resource,
    ) = message_tree

    config.segment_trunc_fn = partial(MemoryTruncationFunctions.segment_fn_last_n, n=1)
    trunc_memory = MemoryResource("memory_1", config)

    memory = trunc_memory.get_memory(last_action_message).memory
    memory_without_prompt = memory.replace("initial prompt\n\n", "")
    memory_segments = memory_without_prompt.split("!!")

    expected_prev_phases_memory = [
        "<TRUNC>",
        "[phase_0_agent_1]phase_0_agent_1_action",
    ]

    memory_segments[0] == " ".join(expected_prev_phases_memory)


def test_messages_with_version(message_tree):
    (
        last_action_message,
        last_agent_message,
        last_phase_message,
        config,
        mem_resource,
    ) = message_tree

    agent0 = last_agent_message.prev

    new_agent0 = AgentMessage("new_agent_0", "new_agent_0")

    new_agent0.set_prev(agent0.prev)
    new_agent0.set_next(agent0.next)
    agent0.parent.add_child_message(new_agent0)

    new_agent0.set_version_prev(agent0)

    memory = mem_resource.get_memory(new_agent0).memory

    assert agent0.agent_id not in memory
    assert new_agent0.agent_id in memory



def test_get_memory_from_message_with_next(message_tree):
    """
    Even if memory-generating message is not the latest message (i.e. has next),
    it should still generate memory the same way.
    """
    (
        last_action_message,
        last_agent_message,
        last_phase_message,
        config,
        mem_resource,
    ) = message_tree

    before_link = mem_resource.get_memory(last_agent_message).memory
    _ = AgentMessage("new_agent", prev=last_agent_message)
    after_link = mem_resource.get_memory(last_agent_message).memory

    assert before_link == after_link
