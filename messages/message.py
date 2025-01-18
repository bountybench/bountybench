from abc import ABC
import time
class Message(ABC): 
    _next: 'Message' = None

    def __init__(self, prev: 'Message' = None) -> None:
        self._prev = prev
        if prev is not None and hasattr(prev, 'set_next'):
            prev.set_next(self)
            
        self.timestamp = time.strftime('%Y-%m-%dT%H:%M:%S%z')
        self._id = id(self)
        from messages.message_utils import log_message
        log_message(self)

    @property
    def prev(self) -> str:
        return self._prev
    
    @property
    def next(self) -> str:
        return self._next
    
    @property
    def id(self) -> str:
        return self._id
    
    def set_next(self, next: 'Message') -> None:
        self._next = next
    
    def to_dict(self) -> dict:
        return {
            "prev": id(self.prev) if self.prev else None,
            "current_id": self.id,
            "next": id(self.next) if self.next else None,
            "timestamp": self.timestamp
        }
    
