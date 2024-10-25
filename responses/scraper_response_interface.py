from abc import ABC

class ScraperResponseInterface(ABC):
    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is ScraperResponseInterface:
            return all(
                any(attr in B.__dict__ for B in subclass.__mro__)
                for attr in ['bounty_program_name', 'bounty_link', 'response']
            )
        return NotImplemented
