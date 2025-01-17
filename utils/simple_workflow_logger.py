import json
import os
from pathlib import Path
from typing import Any, Dict, List

class SimpleWorkflowLogger:
    def __init__(self, log_file: str = "messages_log.json"):
        self.log_file = Path(log_file)
        # Create if it doesn't exist
        if not self.log_file.exists():
            with open(self.log_file, 'w') as f:
                json.dump([], f)  # Start with empty list

    def write(self, message_data: Dict[str, Any]) -> None:
        """
        Append the given message data (already in dict form) to the JSON file.
        """
        # Read existing
        with open(self.log_file, 'r') as f:
            all_messages: List[Dict[str, Any]] = json.load(f)

        # Append
        all_messages.append(message_data)

        # Write back
        with open(self.log_file, 'w') as f:
            json.dump(all_messages, f, indent=4)

    def clear_log(self) -> None:
        """Convenience method to clear the log file."""
        with open(self.log_file, 'w') as f:
            json.dump([], f)

logger = SimpleWorkflowLogger()