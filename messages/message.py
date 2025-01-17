from abc import ABC
class Message(ABC): 
    _next: 'Message' = None

    def __init__(self, prev: 'Message' = None) -> None:
        self._prev = prev
        if prev is not None and hasattr(prev, 'set_next'):
            prev.set_next(self)
        else:
            print(f"Warning: prev is not a Message object. Type: {type(prev)}")

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
            "prev": self.prev,
            "next": self.next
        }