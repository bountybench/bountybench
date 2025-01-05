from typing import List

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from messages.message import Message


class MessageHistory:
    def __init__(self):
        self.messages: List[Message] = []
        self.model = SentenceTransformer('all-MiniLM-L6-v2', tokenizer_kwargs={'clean_up_tokenization_spaces': True})

    def log(self, message: Message):
        self.messages.append(message)

    def is_repetitive(self, current_message: Message, n: int = 3, threshold: float = 0.8) -> bool:
        if len(self.messages) < n:
            return False
        recent_messages = self.messages[-n:]
        current_embedding = self.model.encode(current_message.message)
        for resp in recent_messages:
            resp_embedding = self.model.encode(resp.message)
            similarity_score = cosine_similarity(
                [current_embedding], [resp_embedding])[0][0]
            if similarity_score < threshold:
                return False
        return True
