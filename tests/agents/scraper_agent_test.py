from agents.scraper_agent.scraper_agent import ScraperAgent

scraper_agent = ScraperAgent()
response = scraper_agent.run([])
print(response.response)
