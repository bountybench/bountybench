import json
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent

REPO_BOUNTY = [
    ("InvokeAI", 0),
    ("Librechat", 0),
    ("Librechat", 1),
    ("Librechat", 3),
    ("agentscope", 0),
    ("astropy", 0),
    ("bentoml", 0),
    ("bentoml", 1),
    ("composio", 0),
    ("fastapi", 0),
    ("gluon-cv", 0),
    ("gpt_academic", 0),
    ("gradio", 0),
    ("gradio", 1),
    ("gradio", 2),
    ("gunicorn", 0),
    ("kedro", 0),
    ("lunary", 0),
    ("lunary", 1),
    ("lunary", 2),
    ("mlflow", 0),
    ("mlflow", 1),
    ("mlflow", 2),
    ("mlflow", 3),
    ("open-webui", 0),
    ("parse-url", 0),
    ("scikit-learn", 0),
    ("setuptools", 0),
    ("undici", 0),
    ("vllm", 0),
    ("yaml", 0),
    ("zipp", 0),
]


def list_metadata_objects(directory: Path = Path("./bountybench")) -> Dict[str, Any]:
    """
    List all bounty metadata objects in the bountybench directory.
    """
    results_dict = {}

    for repo, bounty in REPO_BOUNTY:
        bounty_dir_path = (
            PROJECT_ROOT / "bountybench" / repo / "bounties" / f"bounty_{bounty}"
        )
        metadata_path = bounty_dir_path / "bounty_metadata.json"
        if not bounty_dir_path.exists() or not metadata_path.exists():
            raise FileNotFoundError(
                f"Metadata file not found for {repo} bounty {bounty} at {metadata_path}"
            )

        with open(bounty_dir_path / "bounty_metadata.json", "r") as f:
            bounty_metadata = json.load(f)
        results_dict[(repo, bounty)] = bounty_metadata

    return results_dict


def write_to_metadata(repo: str, bounty: int, field: str, value: Any) -> None:
    """
    Write a field to the bounty metadata file.
    """
    bounty_dir_path = (
        PROJECT_ROOT / "bountybench" / repo / "bounties" / f"bounty_{bounty}"
    )
    metadata_path = bounty_dir_path / "bounty_metadata.json"

    if not bounty_dir_path.exists() or not metadata_path.exists():
        raise FileNotFoundError(
            f"Metadata file not found for {repo} bounty {bounty} at {metadata_path}"
        )

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    metadata[field] = value

    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Updated {field} in {repo} bounty {bounty} metadata.")


def read_from_metadata(repo: str, bounty: int, field: str) -> Any:
    """
    Read a field from the bounty metadata file.
    """
    bounty_dir_path = (
        PROJECT_ROOT / "bountybench" / repo / "bounties" / f"bounty_{bounty}"
    )
    metadata_path = bounty_dir_path / "bounty_metadata.json"

    if not bounty_dir_path.exists() or not metadata_path.exists():
        raise FileNotFoundError(
            f"Metadata file not found for {repo} bounty {bounty} at {metadata_path}"
        )

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    return metadata.get(field, None)


def delete_from_metadata(repo: str, bounty: int, field: str) -> None:
    """
    Delete a field from the bounty metadata file.
    """
    bounty_dir_path = (
        PROJECT_ROOT / "bountybench" / repo / "bounties" / f"bounty_{bounty}"
    )
    metadata_path = bounty_dir_path / "bounty_metadata.json"

    if not bounty_dir_path.exists() or not metadata_path.exists():
        raise FileNotFoundError(
            f"Metadata file not found for {repo} bounty {bounty} at {metadata_path}"
        )

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    if field in metadata:
        del metadata[field]

    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Deleted {field} from {repo} bounty {bounty} metadata.")
