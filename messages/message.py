import time
from abc import ABC


class Message(ABC):    
    @classmethod
    def _get_message_type(cls):
        if hasattr(cls, '_message_type'):
            return cls._message_type
        return cls.__name__

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        from messages.message_utils import register_message_class
        register_message_class(cls)

    def __init__(self, prev: "Message" = None, attrs: dict = None) -> None:
        self._prev = prev
        if prev and hasattr(prev, "set_next"):
            prev.set_next(self)
        self._next = None
        self._version_prev = None
        self._version_next = None
        self._parent = None
        self._timestamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        self._id = str(id(self))

        if attrs:
            self._initialize_from_dict(attrs)

        from messages.message_utils import register_message

        register_message(self)

    def _initialize_from_dict(self, attrs: dict) -> None:
        for key, value in attrs.items():
            setattr(self, f"_{key}", value)

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        attrs = {
            "prev": data.get("prev"),
            "next": data.get("next"),
            "version_prev": data.get("version_prev"),
            "version_next": data.get("version_next"),
            "parent": data.get("parent"),
            "current_id": data.get("current_id"),
            "timestamp": data.get("timestamp"),
        }
        return cls(attrs=attrs)

    @property
    def workflow_id(self) -> str:
        return None

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

    @property
    def timestamp(self) -> str:
        return self._timestamp

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

    def set_parent(self, parent: "Message") -> None:
        self._parent = parent

    def set_prev(self, prev: "Message") -> None:
        self._prev = prev

    def set_next(self, next: "Message") -> None:
        self._next = next

    def set_version_prev(self, version_prev: "Message") -> None:
        self._version_prev = version_prev
        version_prev._version_next = self

    def set_additional_attrs(self, data: dict) -> None:
        for key, value in data.items():
            setattr(self, key, value)

    @property
    def message_type(self) -> str:
        """
        Return the type of this message. By default, use the class name.
        Subclasses can override or rely on the base class name.
        """
        if hasattr(self, "_message_type"):
            return self._message_type
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
