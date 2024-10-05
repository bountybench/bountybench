
planning_agent_config = AgentConfig(
    prompt=planning_prompt,
    iterations=5
)
planner = Agent(planning_agent_config)
executor_agent_config = AgentConfig(
    prompt=executor_prompt,
    iterations=5
)
executor = Agent(executor_agent_config)
executor2 = Agent(executor_agent_config2)


p_response = planner.run(init_prompt)

# make sure both are running asynchronous, imagine separate threads v processes
e_response = executor.run([p_response])
e2_response = executor2.run([p_response])

e_responses = [e_response, e2_response]

planner.run(e_responses)
