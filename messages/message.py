import time
from abc import ABC
from typing import List


class Message(ABC):

    def __init__(self, prev: "Message" = None) -> None:
        self._prev = None
        self._next = None
        self._version_prev = None
        self._version_next = None
        self._parent = None

        self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        self._id = str(id(self))
        self._set_parent_from_context()

    def _set_parent_from_context(self):
        """Override this method in subclasses to set the parent message from the context."""
        pass

        self._set_parent_from_context()
        # Message structure is tiered - messages can only have direct links within the same parent
        # If no parent gets set, assume message can be linked to any other message
        if prev and (not self.parent or prev.parent == self.parent):
            self._prev = prev
            if hasattr(prev, "set_next"):
                prev.set_next(self)

    def _set_parent_from_context(self):
        """Override this method in subclasses to set the parent message from the context."""
        pass

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

    def get_latest_version(self):
        message = self
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

    @property
    def versions(self) -> List[str]:
        message = self
        versions = [message.id]
        while message.version_prev:
            message = message.version_prev
            versions.insert(0, message.id)
        message = self
        while message.version_next:
            message = message.version_next
            versions.append(message.id)

        return versions

    @property
    def message_type(self) -> str:
        """
        Return the type of this message. By default, use the class name.
        Subclasses can override or rely on the base class name.
        """
        return self.__class__.__name__

    def to_base_dict(self) -> dict:
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

    def to_broadcast_dict(self) -> dict:
        base_dict = self.to_base_dict()
        if self.parent is not None:
            base_dict["parent"] = self.parent.id
        if len(self.versions) > 1:
            base_dict["versions"] = self.versions

        return base_dict

    def to_log_dict(self) -> dict:
        log_dict = self.to_base_dict()
        return log_dict
