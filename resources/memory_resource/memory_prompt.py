import string

from resources.memory_resource.memory_scope import MemoryScope


class MemoryPrompts:
    """Collection of format strings to convert memory to prompt."""

    _DEFAULT_SEGUE = (
        "In addition to the above task, "
        "you are also provided the transaction history of the system.\n"
        "You should account for previous messages (if present) "
        "that have occurred when formulating your response:"
    )

    _DEFAULT_SEGMENTS = (
        " * {prev_phase_messages}\n"
        " * {prev_agent_messages}\n"
        " * {prev_action_messages}"
    )

    DEFAULT_FMT_WORKFLOW = "\n".join([_DEFAULT_SEGUE, _DEFAULT_SEGMENTS])
    DEFAULT_FMT_PHASE = "\n".join(
        [_DEFAULT_SEGUE, "\n".join(_DEFAULT_SEGMENTS.split("\n")[1:])]
    )
    DEFAULT_FMT_AGENT = "\n".join(
        [_DEFAULT_SEGUE, "\n".join(_DEFAULT_SEGMENTS.split("\n")[2:])]
    )

    @staticmethod
    def validate_memory_prompt(prompt, scope: MemoryScope):
        kwargs = ["prev_phase_messages", "prev_agent_messages", "prev_action_messages"][
            scope.value :
        ]
        kwargs = set(kwargs)

        user_keys = set(
            x[1] for x in string.Formatter().parse(prompt) if x[1] is not None
        )

        if user_keys != kwargs:
            diffs = (user_keys - kwargs) | (kwargs - user_keys)
            raise ValueError(
                f"Format string does not match expected input for {str(scope)}\n"
                f"Expected format string kwargs: {kwargs}\n"
                f"Inputted format string kwargs: {user_keys}\n"
                f"Mismatched kwargs: {diffs}"
            )
