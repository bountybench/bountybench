from typing import List, Optional
import json


def parse_json(text: str) -> Optional[dict]:
    """Parses a string to a JSON object.

    Args:
        text: The string to parse.

    Returns:
        A JSON object if the string is valid JSON, otherwise None.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def parse_field(
    text: str, field: str, multiline: bool = True, stop_str: Optional[str] = None
) -> Optional[str]:
    """
    Extracts a field value from the input text based on the given field name.

    Parameters:
    - text: The input string to search.
    - field: The name of the field to extract.
    - multiline: If True, extracts multiple lines until
        an optional stop string or the end of the text.
    - stop_str: An optional string that defines where the field extraction should stop.

    Returns:
    - The extracted field value as a string if found, or None if not found.
    """
    if text == "":
        return None

    # Find the start index for the field
    field_marker = f"{field}"
    start_index = text.lower().find(field_marker.lower())
    if start_index == -1:
        # Field not found
        return None

    # Move index to the end of the field marker
    start_index += len(field_marker)

    # Define where to stop extraction
    if stop_str:
        stop_index = text.lower().find(stop_str.lower(), start_index)
        if stop_index == -1:
            stop_index = len(
                text
            )  # Stop at the end of the text if stop_str is not found
    else:
        stop_index = len(text)

    # Extract the substring
    extracted_field = text[start_index:stop_index].strip()
    # If multiline is False, only return the first line
    if not multiline:
        extracted_field = extracted_field.split("\n", 1)[0].strip()

    return extracted_field if extracted_field else None


def extract_command(message: str, stop_str: str) -> List[str]:
    command = parse_field(message, "Command:", stop_str=stop_str)
    if not command:
        raise Exception("Command is missing from message, cannot be a command message.")
    command = command.lstrip().lstrip("*").lstrip()
    return command


def extract_memory(message: str, stop_str: str = "Command:") -> Optional[dict]:
    memory = parse_field(message, "Memory:", stop_str=stop_str)
    if not memory:
        return None
    memory = memory.lstrip().lstrip("*").strip()
    memory_dict = parse_json(memory)
    return memory_dict
