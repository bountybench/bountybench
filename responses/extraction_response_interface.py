from abc import ABC

class ExtractionResponseInterface(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is ExtractionResponseInterface:
            return all(
                any(attr in B.__dict__ for B in subclass.__mro__)
                for attr in ['response', 'description', 'proof', 'bug_commit', 'bug_tag', 'patch_commit', 'patch_tag', 'metadata', 'link']
            )
        return NotImplemented
