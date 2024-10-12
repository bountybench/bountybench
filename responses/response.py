import re
from abc import ABC
from typing import Optional

class Response(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        return any('response' in B.__dict__ for B in subclass.__mro__)

    @staticmethod
    def parse_field(text: str, field: str, multiline: bool = False, stop_str: Optional[str] = None) -> Optional[str]:
        """
        Extracts a field value from the input text based on the given field name.
        
        Parameters:
        - text: The input string to search.
        - field: The name of the field to extract.
        - multiline: If True, extracts multiple lines until an optional stop string or the end of the text.
        - stop_str: An optional string that defines where the field extraction should stop.
        
        Returns:
        - The extracted field value as a string if found, or None if not found.
        """
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
                stop_index = len(text)  # Stop at the end of the text if stop_str is not found
        else:
            stop_index = len(text)
        
        # Extract the substring
        extracted_field = text[start_index:stop_index].strip()

        # If multiline is False, only return the first line
        if not multiline:
            extracted_field = extracted_field.split('\n', 1)[0].strip()

        return extracted_field if extracted_field else None