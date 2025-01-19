"""
Later write an abstract class for agents or smth to ensure uniformty / share some goodies
"""
from agents.planner_agent.prompt import PLANNER_BASE_PROMPT
from agents.base_agent import BaseAgent

class PlannerAgent(BaseAgent):

    def __init__(self, config):
        self.config = config

    def formulate_prompt_from_initial_goal():
        self.prompt = PLANNER_BASE_PROMPT

