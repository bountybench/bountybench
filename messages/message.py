from abc import ABC
class Message(ABC): 
    _next: 'Message' = None

    def __init__(self, message: str, prev: 'Message' = None) -> None:
        prev.set_next(self)
        self._message = message
        self._prev = prev

    @property
    def message(self) -> str:
        return self._message
    
    @property
    def prev(self) -> str:
        return self._prev
    
    @property
    def next(self) -> str:
        return self._next
    
    def set_next(self, next: 'Message') -> None:
        self._next = next
    
    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "prev": self.prev,
            "next": self.next
        }