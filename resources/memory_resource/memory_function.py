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
    def segment_fn_last_n(segment, n=3):
        """Keep last n messages in each segment."""
        trunc_token = "..."

        if len(segment) <= n:
            return segment

        truncated = [trunc_token] + segment[-n:]
        return truncated

    @staticmethod
    def segment_fn_noop(segment):
        """No-op segment truncation."""
        return segment

    @staticmethod
    def memory_fn_noop(segments):
        """No-op memory truncation."""
        return segments

    @staticmethod
    def memory_fn_by_token(segments, max_input_tokens=4096):
        trunc_token = "Message is too long. Truncating here..."

        max_tokens_per_segment = [max_input_tokens // len(segments)] * len(segments)
        max_tokens_per_segment[-1] += max_input_tokens - sum(max_tokens_per_segment)

        truncated = []

        for i, segment in enumerate(segments):
            cnt = 0

            trunc_segment = [None for _ in range(len(segment))]
            trunc_flag = False

            for j in range(len(segment) - 1, -1, -1):
                tokens = segment[j].split()
                cnt += len(tokens)

                if cnt >= max_tokens_per_segment[i]:
                    if not trunc_flag:
                        trunc = " ".join(tokens[cnt - max_tokens_per_segment[i] :])
                        trunc_segment[j] = trunc_token + trunc
                        trunc_flag = True
                    continue

                trunc_segment[j] = segment[j]

            truncated.append([x for x in trunc_segment if x is not None])

        return truncated

    @staticmethod
    def memory_fn_by_message_token(
        segments, max_message_input_tokens=1024
    ):
        trunc_token = "Message is too long. Truncating here..."

        truncated = []

        for segment in segments:
            trunc_segment = [None for _ in range(len(segment))]

            for j, msg in enumerate(segment):
                tokens = msg.split()
                cnt = len(tokens)

                if cnt > max_message_input_tokens:
                    # Calculate how many tokens to keep from start and end
                    half_tokens = max_message_input_tokens // 2
                    start_tokens = tokens[:half_tokens]
                    end_tokens = tokens[-half_tokens:]

                    # Combine with truncation token in the middle
                    truncated_msg = (
                        " ".join(start_tokens)
                        + "\n"
                        + trunc_token
                        + "\n"
                        + " ".join(end_tokens)
                    )
                    trunc_segment[j] = truncated_msg
                else:
                    trunc_segment[j] = msg

            truncated.append([x for x in trunc_segment if x is not None])

        return truncated
