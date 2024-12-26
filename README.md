# bountyagent

python -m venv myenv
pip install -r common_requirements.txt
python3 -m workflows.exploit_and_patch_workflow_v2 --task_repo_dir bountybench/astropy --bounty_number 0 --interactive
