import json
import uuid
from typing import Any, Dict, List


class ChatChain:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.chain: List[Dict[str, Any]] = []
        self.model_response_index: List[int] = []
        self.assistant_observation_index: List[int] = []

    def append(self, message: Dict[str, Any]) -> None:
        self.chain.append(message)

    def save_chat_chain_as_json(self, file_path: str) -> None:
        with open(file_path, "w") as file:
            json.dump(self.chain, file)

    def load_chat_chain(self, file_path: str) -> None:
        with open(file_path, "r") as file:
            self.chain = json.load(file)

    def clear(self) -> None:
        self.chain.clear()

    def __str__(self) -> str:
        return "\n".join(
            f"\n----------Message from {msg['role']}----------\n{msg['content']}"
            for msg in self.chain
        )
   
