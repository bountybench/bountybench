from abc import ABC

class ExtractionAgentMessageInterface(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is ExtractionAgentMessageInterface:
            return all(
                any(attr in B.__dict__ for B in subclass.__mro__)
                for attr in ['message', 'description', 'proof', 'bug_commit', 'bug_tag', 'patch_commit', 'patch_tag', 'metadata', 'link']
            )
        return NotImplemented
