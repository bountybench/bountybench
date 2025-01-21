from abc import ABC
import time

class Message(ABC): 

    def __init__(self, prev: 'Message' = None) -> None:
        self._prev = prev
        if prev is not None and hasattr(prev, 'set_next'):
            prev.set_next(self)
            
        self._next = None
        self._version_prev = None
        self._version_next = None
        self._parent = None
        
        self.timestamp = time.strftime('%Y-%m-%dT%H:%M:%S%z')
        self._id = str(id(self))
        from messages.message_utils import log_message
        log_message(self)

    @property
    def prev(self) -> str:
        return self._prev
    
    @property
    def next(self) -> str:
        return self._next
    
    @property
    def version_prev(self) -> str:
        return self._version_prev
    
    @property
    def version_next(self) -> str:
        return self._version_next
    
    def get_latest_version(self, message):
        while message.version_next:
            message = message.version_next
        return message
    
    @property
    def id(self) -> str:
        return self._id
    
    @property
    def parent(self) -> str:
        return self._parent
    
    def set_parent(self, parent: 'Message') -> None:
        self._parent = parent
    
    def set_next(self, next: 'Message') -> None:
        self._next = next
    
    def set_version_prev(self, version_prev: 'Message') -> None:
        self._version_prev = version_prev
        version_prev._version_next = self
    
    @property
    def message_type(self) -> str:
        """
        Return the type of this message. By default, use the class name.
        Subclasses can override or rely on the base class name.
        """
        return self.__class__.__name__
    
    def to_dict(self) -> dict:
            result = {}
            result["message_type"] = self.message_type
            if self.prev is not None:
                result["prev"] = self.prev.id
            
            result["current_id"] = self.id
            
            if self.next is not None:
                result["next"] = self.next.id
            if self.version_prev is not None:
                result["version_prev"] = id(self.version_prev)
            if self.version_next is not None:
                result["version_next"] = id(self.version_next)
            
            result["timestamp"] = self.timestamp
            
        
            return result