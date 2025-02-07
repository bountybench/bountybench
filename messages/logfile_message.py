import json

from messages.workflow_message import WorkflowMessage


def load_workflow_from_json(file_path: str) -> WorkflowMessage:
    with open(file_path, "r") as json_file:
        data = json.load(json_file)
        return WorkflowMessage.from_dict(data)
