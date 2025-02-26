from datetime import datetime
import os
import subprocess
import sys

import yaml
from fastapi import APIRouter, HTTPException

from backend.schema import ExperimentConfig

parallel_run_router = APIRouter()



@parallel_run_router.post("/workflow/parallel-run")
async def start_parallel_run(experiment_config: ExperimentConfig):
    """Start a parallel run experiment using form data."""
    script_path = os.path.join(os.getcwd(), "backend", "ui_experiment_runner.py")

    if not os.path.exists(script_path):
        raise HTTPException(status_code=500, detail="ui_experiment_runner.py not found")

    try:
        # Load YAML string into dictionary
        yaml_data = yaml.safe_load(experiment_config.config)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Define a temporary YAML file path
        temp_config_path = os.path.join(
            os.getcwd(), "configs", f"parallel_workflow_config_{timestamp}.yaml"
        )

        # Save the parsed YAML as a file
        with open(temp_config_path, "w") as file:
            yaml.dump(yaml_data, file, default_flow_style=False)

        # Ensure YAML file exists
        if not os.path.exists(temp_config_path):
            raise HTTPException(status_code=500, detail="Failed to create config file")

        # Run the experiment script with the generated YAML file
        process = subprocess.Popen(
            [sys.executable, script_path, temp_config_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        return {
            "status": "started",
            "pid": process.pid,
            "config_path": temp_config_path,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
