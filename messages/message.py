from abc import ABC

from utils import workflow_logger
class Message(ABC): 
    _next: 'Message' = None

    def __init__(self, prev: 'Message' = None, auto_log: bool = False) -> None:
        if prev:
            prev.set_next(self)
        self._prev = prev

        if auto_log:
            self.log_message()
    
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
    

