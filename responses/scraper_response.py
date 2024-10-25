from responses.scraper_response_interface import  ScraperResponseInterface

class ScraperResponse(ScraperResponseInterface):
    def __init__(self, response: str) -> None:
        self._response = response
        self._bounty_program_name = None
        self._bounty_link = None
 
    @property
    def response(self) -> str:
        return self._response

    @property
    def bounty_program_name(self) -> str:
        return self._bounty_program_name
    
    @property
    def bounty_program_name(self) -> str:
        return self._bounty_link