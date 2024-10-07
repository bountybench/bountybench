

args = parse_args()
agent = SimpleExecutionAgent(response_history=3, max_input_tokens=...)
response = agent.run()
for i in range(args.num_iterations):
    response = agent.run(response)
    if issubclass(response.__class__, AnswerResponseInterface):
        print(check_response_answer(response))
        break
