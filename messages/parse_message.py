from typing import List, Optional


def parse_field(
    text: str,
    field: str,
    multiline: bool = True,
    stop_str: Optional[str] = None,
    from_end: Optional[bool] = True,
) -> Optional[str]:
    """
    Extracts a field value from the input text based on the given field name.

    Parameters:
    - text: The input string to search.
    - field: The name of the field to extract.
    - multiline: If True, extracts multiple lines until an optional stop string or the end of the text.
    - stop_str: An optional string that defines where the field extraction should stop.
    - from_end: If True, finds the last instance of the field in the text instead of the first.

    Returns:
    - The extracted field value as a string if found, or None if not found.
    """
    if text is None:
        return None

    # Find the start index for the field
    field_marker = f"{field}"

    if from_end:
        start_index = text.lower().rfind(field_marker.lower())
    else:
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
