import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

logs_router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"


def parse_log_metadata(file_path):
    try:
        with open(file_path, "r") as f:
            try:
                data = json.load(f)
                if not data:
                    print(f"Empty data in {file_path}")
                    return None

            except json.JSONDecodeError as json_err:
                print(f"JSON parsing error in {file_path}: {str(json_err)}")
                return None

            metadata = data.get("workflow_metadata", {})
            workflow_summary = metadata.get("workflow_summary", {})
            if isinstance(workflow_summary, str):
                if workflow_summary == "incomplete":
                    workflow_summary = {"complete": False, "success": False}
                else:
                    summary_parts = workflow_summary.split("_")
                    if len(summary_parts) == 2:
                        workflow_summary = {
                            "complete": workflow_summary.split("_")[0] == "completed",
                            "success": workflow_summary.split("_")[1] == "success",
                        }
                    else:
                        workflow_summary = {"complete": False, "success": False}
            elif not workflow_summary:
                workflow_summary = {"complete": False, "success": False}

            task = metadata.get("task", {})

            return {
                "filename": file_path.name,
                "workflow_name": metadata.get("workflow_name"),
                "complete": workflow_summary.get("complete"),
                "success": workflow_summary.get("success"),
                "task_dir": task.get("task_dir") if task else "",
                "bounty_number": task.get("bounty_number") if task else "",
                "task_id": (
                    f"{task.get('task_dir')}_{task.get('bounty_number')}"
                    if task
                    else ""
                ),
            }
    except Exception as e:
        print(f"Error parsing {file_path}: {str(e)}")
        return None


@logs_router.get("/logs")
async def list_logs():
    """
    List all JSON log files in the directory with metadata
    """
    try:
        if not LOG_DIR.exists():
            raise HTTPException(status_code=404, detail="Log directory not found")

        files = LOG_DIR.rglob("*.json")
        logs_data = [parse_log_metadata(f) for f in files if f.is_file()]
        logs_data = [log for log in logs_data if log is not None]

        return JSONResponse(content=logs_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@logs_router.get("/logs/{filename}")
async def get_log(filename: str):
    """
    Retrieve the content of a specific JSON log file.
    """
    file_path = LOG_DIR / filename
    if not file_path.exists() or not file_path.suffix == ".json":
        raise HTTPException(status_code=404, detail="Log file not found")
    try:
        return FileResponse(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
