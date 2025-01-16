from abc import ABC

class AgentMessageInterface(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is AgentMessageInterface:
            return all(
                any(attr in B.__dict__ for B in subclass.__mro__)
                for attr in ['agent_id', 'actions']
            )
        return NotImplemented