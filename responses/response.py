import re
from abc import ABC
from typing import Optional

class Response(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is CommandResponseInterface:
            return any('response' in B.__dict__ for B in subclass.__mro__)
        return NotImplemented

def parse_field(text: str, field: str, case_sensitive:bool=False, stop_str:Optional[str]=None) -> str:
    """
    Takes in the name of a field and returns the field corresponding to that string using regex
    regex parses starting from field until the optional stop_str
    
    Assumptions:
    - The field will always be formatted as 'field_name: ' (e.g., 'command: ')
    
    :param text: The input string from which to extract the field.
    """
    # Define flags for case sensitivity
    flags = 0 if case_sensitive else re.IGNORECASE

    # Build the regular expression, with optional stop_str
    if stop_str:
        # Make stop_str optional using `|` (OR) to handle cases where it doesn't exist
        regex = rf"{re.escape(field)}(.*?)(?:{re.escape(stop_str)}|$)"
    else:
        regex = rf"{re.escape(field)}(.*?)$"
    
    # Search the text using the regex
    match = re.search(regex, text, flags)

    # If the match was found, return the extracted field value
    if match:
        return match.group(1).strip()
    
    return ""

