from typing import List

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from responses.response import Response


class ResponseHistory:
    def __init__(self):
        self.responses: List[Response] = []
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def log(self, response: Response):
        self.responses.append(response)

    def is_repetitive(self, current_response: Response, n: int = 3, threshold: float = 0.8) -> bool:
        if len(self.responses) < n:
            return False
        recent_responses = self.responses[-n:]
        current_embedding = self.model.encode(current_response.response)
        for resp in recent_responses:
            resp_embedding = self.model.encode(resp.response)
            similarity_score = cosine_similarity(
                [current_embedding], [resp_embedding])[0][0]
            if similarity_score < threshold:
                return False
        return True
