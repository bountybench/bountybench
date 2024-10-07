"""
First note: there must be some way of instantiating agents.

Think through what parameters it must take and what happens once it's instantiated.

Is it a separate thread / process / node? Is it just an object? What does this look like? And how to do we generalize for all use cases?
"""

"""
Pseudocode:

(1) Instantiate planning agent
    a) Define Planning Agent config
    b) Instantiate the Agent
(2) Instantiate the executor agent(s)
Design question: Should the planning agent be spinning up the executor agents or should we pre-spin them up? I think we should support agents starting new agents.

It's probably also work thinking through the lifespan of a given agent/node. Are they spun up for a single workflow or continuous to be taking on tasks? Both types should be supported.
(3) Have the planning agent come up with a plan
Thought: somehow this plan needs to distribute to several executors. Should the executors all receive the same plan but have different prompts / backgrounds that they are able to ingest the same plan and do different work that is useful? Or should the onus be upstream on the planning?

i.e. the question is one of responsibility -- who is the one who should be doing what. A common question for objects, functions, code etc.

I'm leaning toward a stupid planner and smarter downstream.

The reason because we can pre-program downstream and fix downstream workflow prompts with human prompts, which are less stochastic.
(4) Executors run for n iterations
This is a little strange under the current paradigm. They create ExecutorResponses which they then take themselves and then continue running. Should the continue running yourself be a special case or work in the general case?

I'd actually go with the general case even though it seems extra.

Basically here the initial ExecutorResponse would be
[run for N iterations] but should we really be hard coding N or should we have upstream do it? Since it may depend on 

Ok I think it's fine to have a List[Prompt]; for now we can keep things simple and focus on len(list) = 1 but this support generality as necessary.

This would basically be parse(response) -> List[Prompt]

maybe not

well the question is, who should be responsible for the parse(response) fucntion. 

probalby upstream since that is just a more intuitive way to write code

and there's still flexiblity:

wait no

the issue is should upstream agent (response)

custom prompts for downstream agents. should upstream agent be responsible for their prompts

this might be easier where I know I subscribe to X response and I will write an agent to create Y prompt then iterate to yield Z response

we have to do this for colalboration 

my suspicion is most agent development will be in self loop
will run for 5-10 iterations

whether web investigation / 

i don't think ai will have a good intuition of iteration or upstream 
"""
planning_agent_config = AgentConfig(
    prompt=planning_prompt,
    iterations=5
)
planner = Agent(planning_agent_config)
executor = Agent(executor_agent_config)

while iterations < max_iterations and not stop_condition:
    plan = planner.run(environment ... )
    response = executor.run(plan ...)


response_1 = Agent(prompt_1)
prompt_2 = simple_parse(response_1)
# where parse does truncation etc.
response_2 = Agent(prompt_2)


while not stop_condition:
    planning_response_1 = PlanningAgent(planning_prompt_1)
    execute_prompt_1 = smart_parse_plan_to_execution_prompt(planning_response_1)
        # here parse does a little bit more clever thing

    execute_responses = []
    for i in range(iterations):
        execute_response_1 = ExecuteAgent(execute_prompt_1)
        execute_prompt_1 = simple_parse(execute_response_1)
        execute_responses.append(execute_response_1)

    planning_prompt_2 = smart_parse_execution_back_to_planning(prompt_1, planning_response_1, execute_responses)
    planning_prompt_1 = planning_prompt_2 

"""
1) translating using "parse logic"
some notion of parsing responses feels very fundamental / translation

translating prompts is how you go between agents
"""
