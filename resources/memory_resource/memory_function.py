ITERATIONS_TO_KEEP = 3
MSG_TOKEN_LIMIT = [1536, 512, 128]  # r_t, o_k_t, o_p_t


class MemoryCollationFunctions:
    """
    Collection of memory collation functions.

    Collation functions should take a list of messages of a single segment,
    e.g., prev_agent_messages, and convert it into a single string.
    Each memory can have up to three segments, as defined in MemoryPrompts.
    """

    @staticmethod
    def collate_ordered(segment, start=1):
        """Join each message and prepend enumeration."""
        return "\n".join(f"{i+start}) {message}" for i, message in enumerate(segment))

    @staticmethod
    def validate_collation_fn(fn):
        assert (
            type(fn(["msg1", "msg2"])) == str
        ), "Memory collation_fn should take list of messages and output str."


class MemoryTruncationFunctions:
    """
    Collection of memory truncation functions.

    There are two types of truncation functions.
     - segment_fn*: Takes a list of messages in a single segment,
        and returns a truncated segment.
     - memory_fn*: Takes a list of segments (ie list of lists),
        and returns a globally truncated memory.
    """

    @staticmethod
    def segment_fn_last_n(
        segment,
        n=ITERATIONS_TO_KEEP,
        msg_per_iteration=len(MSG_TOKEN_LIMIT)
    ):
        """Keep last n messages in each segment."""
        trunc_token = "..."
        msg_to_keep = n * msg_per_iteration

        if len(segment) <= msg_to_keep:
            return segment

        trunc_segment = [trunc_token] + segment[-msg_to_keep:]
        return trunc_segment

    @staticmethod
    def segment_fn_noop(segment):
        """No-op segment truncation."""
        return segment

    @staticmethod
    def memory_fn_noop(segments):
        """No-op memory truncation."""
        return segments

    @staticmethod
    def memory_fn_by_message_token(
        segments, msg_token_limit=MSG_TOKEN_LIMIT
    ):
        trunc_token = "\n...TRUNCATED...\n"
        msg_per_iteration = len(msg_token_limit)

        truncated = []

        for segment in segments:
            trunc_segment = []

            for j, msg in enumerate(segment):
                tokens = msg.split()
                cnt = len(tokens)
                max_message_input_tokens = msg_token_limit[j % msg_per_iteration] // 2

                if cnt > max_message_input_tokens:
                    # Calculate how many tokens to keep from start and end
                    half_tokens = max_message_input_tokens // 2
                    start_tokens = tokens[:half_tokens]
                    end_tokens = tokens[-half_tokens:]

                    # Combine with truncation token in the middle
                    truncated_msg = (
                        " ".join(start_tokens)
                        + trunc_token
                        + " ".join(end_tokens)
                    )
                    trunc_segment.append(truncated_msg)
                else:
                    trunc_segment.append(msg)

            truncated.append(trunc_segment)

        return truncated
