from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, FileResponse

logs_router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"

@logs_router.get("/logs")
async def list_logs():
    """
    List all JSON log files in the directory.
    """
    try:
        if not LOG_DIR.exists():
            raise HTTPException(status_code=404, detail="Log directory not found")
        files = [f.name for f in LOG_DIR.glob("*.json")]
        return JSONResponse(content=files)
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