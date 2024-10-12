

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the task")
    parser.add_argument(
        "--task_repo_dir", type=str, help="The directory of the task repo"
    )
    parser.add_argument(
        "--bounty_number",
        type=str,
        help="The bounty for the given task; not used in detect_all",
    )
    parser.add_argument(
        "--max_iterations", type=int, help="The maximum number of iterations"
    )
    parser.add_argument(
        "--task_mode",
        type=str,
        help="The mode to use for the agent",
        choices=[task_mode.value for task_mode in TaskModes],
    )
    parser.add_argument(
        "--model",
        type=str,
        help="The model to use for the agent",
        choices=list(
            [model.value for model in ModelRegistry.tokenizers.mapping.keys()]
        ),
    )
    parser.add_argument(
        "--benchmark_id",
        type=str,
        help="The benchmark ID to use for the agent",
    )
    parser.add_argument(
        "--interactive_mode",
        action="store_true",
        help="Use interactive mode for the agent",
    )

    parser.add_argument(
        "--mock_calls",
        action="store_true",
        help="Mock the agent's calls for testing",
    )

    parser.add_argument(
        "--max_input_tokens",
        type=int,
        default=DEFAULT_MAX_INPUT_TOKENS,
        help="Maximum number of input tokens per task run",
    )

    parser.add_argument(
        "--max_output_tokens",
        type=int,
        default=DEFAULT_MAX_OUTPUT_TOKENS,
        help="Maximum number of output tokens per task run",
    )

    parser.add_argument(
        "--responses_to_keep",
        type=int,
        default=3,
        help="Number of responses to keep in the chat chain",
    )

    parser.add_argument(
        "--observations_to_keep",
        type=int,
        default=3,
        help="Number of observations to keep in the chat chain",
    )

    parser.add_argument(
        "--extend_iterations_from_log",
        type=str,
        help="Replay the task from the given file",
        required=False,
    )

    parser.add_argument(
        "--helm",
        action="store_true",
        help="Run the agent using the CRFM-HELM API",
        default=False,
    )
    parser.add_argument(
        "--azure",
        action="store_true",
        help="Run the agent using the Azure OpenAI API",
        default=False,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    repo_metadata = read_repo_metadata(args.task_repo_dir)
    bounty_metadata = read_bounty_metadata(
        args.task_repo_dir, args.bounty_number)

    agent_config = AgentConfig(deployment_name=args.model)

    task_run_config = TaskRunConfig(
        task_mode=TaskModes(args.task_mode),
        max_input_tokens_per_iteration=args.max_input_tokens,
        max_output_tokens_per_iteration=args.max_output_tokens,
        responses_to_keep = args.responses_to_keep,
        observations_to_keep = args.observations_to_keep,
        max_iterations=args.max_iterations,
        start_time_in_ms=int(round(datetime.now().timestamp() * 1000)),
        repo_dir=args.task_repo_dir,
        bounty_dir=(
            args.task_repo_dir + "/metadata/bounty_" + args.bounty_number
            if args.bounty_number
            else None
        ),
    )

    runner = TaskRunner(
        agent_config=agent_config,
        task_run_config=task_run_config,
        benchmark_id=args.benchmark_id,
        repo_metadata=repo_metadata,
        bounty_metadata=bounty_metadata,
    )
    previous_state = None
    if args.extend_iterations_from_log:
        with open(args.extend_iterations_from_log, "r") as file:
            previous_state = json.load(file)

        previous_state_deployment_name = previous_state["agent_config"]["deployment_name"]
        previous_state_task_name = os.path.basename(
            previous_state['task_run_config']["repo_dir"])
        if args.model != previous_state_deployment_name:
            raise ValueError(
                f"Current model {args.model} does not match agent config found in log {previous_state_deployment_name}. "
                "You must use the same model as the one found in the log file to continue your run."
            )
        input_task_name = os.path.basename(args.task_repo_dir)
        if input_task_name != previous_state_task_name:
            raise ValueError(
                f"Input task name: {input_task_name} doesn't match logged task name: {previous_state_task_name}."
            )
        last_iteration = len(
            previous_state["task_run"]["iterations"]
        )
        args.max_iterations = max(args.max_iterations, last_iteration)

    runner.run_task(
        max_input_tokens=args.max_input_tokens,
        max_output_tokens=args.max_output_tokens,
        responses_to_keep=args.responses_to_keep,
        observations_to_keep=args.observations_to_keep,
        helm=args.helm,
        mock_calls=args.mock_calls,
        interactive_mode=args.interactive_mode,
        previous_state=previous_state,
        azure=args.azure,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

args = parse_args()
agent = SimpleExecutionAgent(response_history=3, max_input_tokens=...)
response = agent.run()
for i in range(args.num_iterations):
    response = agent.run(response)
    if issubclass(response.__class__, AnswerResponseInterface):
        print(check_response_answer(response))
        break

