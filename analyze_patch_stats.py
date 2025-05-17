#!/usr/bin/env python3
import os
import json
import subprocess
from typing import Dict, List, Any, Tuple

# List of bounties to analyze
BOUNTIES = [
    "InvokeAI_0", "LibreChat_0", "LibreChat_1", "LibreChat_2", "LibreChat_3",
    "agentscope_0", "astropy_0", "bentoml_0", "bentoml_1",
    "composio_0", "fastapi_0", "gluon-cv_0", "gunicorn_0",
    "kedro_0", "lunary_0", "lunary_1", "lunary_2", "mlflow_0",
    "mlflow_1", "mlflow_2", "mlflow_3", "parse-url_0",
    "scikit-learn_0", "setuptools_0", "undici_0", "vllm_0",
    "yaml_0", "zipp_0", "gradio_0", "gradio_1", "gradio_2",
    "gpt_academic_0", "curl_0", "langchain_1", "langchain_0", "django_0",
    "pytorch-lightning_0", "pytorch-lightning_1", "InvokeAI_1", "LibreChat_4"
]

# Base directory for the 'bountybench' folder - adjust if your script is elsewhere
# Assuming the script is in /Users/joey/VScode/Cyber/dev/bountyagent/
BASE_DIR_BOUNTYBENCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bountybench")
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patch_files_analysis.json")
PATCH_DIFFS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patch_diffs")

def get_current_git_state(repo_path: str) -> str:
    """Gets the current branch or commit hash of a Git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path, capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
             # Fallback to commit hash if not on a branch or other error
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path, capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        
        branch_name = result.stdout.strip()
        if branch_name == "HEAD":  # Detached HEAD state
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path, capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        return branch_name
    except subprocess.CalledProcessError as e:
        print(f"Error getting current Git state for {repo_path}: {e.stderr}")
        raise

def checkout_git_state(repo_path: str, state: str, force_clean: bool = False) -> None:
    """Checks out a specific commit, branch, or tag in a Git repository."""
    try:
        # Stash any local changes first to prevent checkout issues
        subprocess.run(["git", "stash"], cwd=repo_path, capture_output=True, text=True, check=False)

        cmd = ["git", "checkout", state]
        if force_clean:
            cmd.insert(2, "-f") # Force checkout
        
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print(f"Warning: 'git checkout {state}' failed in {repo_path}. Stderr: {result.stderr.strip()}. Retrying with force.")
            # Clean up potential uncommitted changes from failed checkout
            subprocess.run(["git", "reset", "--hard"], cwd=repo_path, capture_output=True, check=False)
            subprocess.run(["git", "clean", "-fdx"], cwd=repo_path, capture_output=True, check=False)
            subprocess.run(["git", "checkout", "-f", state], cwd=repo_path, capture_output=True, text=True, check=True)
        
        print(f"Checked out '{state}' in {repo_path}")
        # Attempt to apply stashed changes, allow failure if no stash
        subprocess.run(["git", "stash", "pop"], cwd=repo_path, capture_output=True, text=True, check=False)

    except subprocess.CalledProcessError as e:
        print(f"Critical Error checking out '{state}' in {repo_path} even after retry: {e.stderr}")
        # Attempt a final cleanup to a known good state if possible (e.g., main/master or original state if passed)
        # This part is tricky without knowing a universally safe branch.
        raise

def count_non_blank_lines(file_path: str) -> int:
    """Counts non-blank lines in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for line in f if line.strip())
    except FileNotFoundError:
        return 0
    except Exception as e:
        print(f"Error counting lines in {file_path}: {e}")
        return 0

def get_diff_output_and_stats(file1_path: str, file2_path: str) -> Tuple[str, int, int]:
    """
    Compares two files using 'git diff --no-index' for full diff and '--shortstat' for stats.
    Returns (full_diff_output, lines_added, lines_removed).
    """
    lines_added = 0
    lines_removed = 0
    try:
        # Get full diff output
        diff_result = subprocess.run(
            ["git", "diff", "--no-index", "--", file1_path, file2_path],
            capture_output=True, text=True, check=False 
        )
        full_diff_output = diff_result.stdout
        # If diff_result.returncode is 0, it means files are identical.
        # If 1, files differ. Other codes might indicate an error.
        if diff_result.returncode > 1:
            print(f"Error in 'git diff --no-index' for '{file1_path}' vs '{file2_path}': {diff_result.stderr.strip()}")
            # Fallback or decide how to handle; for now, return empty diff and 0,0 stats
            # return "", 0, 0 # This might hide issues, better to let shortstat try.

        # Get shortstat for lines added/removed
        shortstat_result = subprocess.run(
            ["git", "diff", "--no-index", "--shortstat", "--", file1_path, file2_path],
            capture_output=True, text=True, check=False
        )
        output = shortstat_result.stdout.strip()

        if "Binary files" in output:
            # For binary files, diff is just a statement, no lines added/removed.
            return f"Binary files {os.path.basename(file1_path)} and {os.path.basename(file2_path)} differ\n", 0, 0
        
        # Check if shortstat itself had an error but diff output might still be valid (e.g. new file)
        if not output and shortstat_result.returncode != 0:
            if full_diff_output: # If full diff exists, maybe it's a new/deleted file scenario not caught by shortstat in a simple way
                pass # proceed to parse what we can from full_diff for lines, or rely on count_non_blank_lines for new files
            else:
                print(f"Git diff --shortstat error for '{file1_path}' vs '{file2_path}': {output} - Return Code: {shortstat_result.returncode}")
                return full_diff_output, 0, 0 # Return the diff we got, but 0,0 for stats

        parts = output.split(',')
        for part in parts:
            part = part.strip()
            if "insertion" in part:
                lines_added = int(part.split()[0])
            elif "deletion" in part:
                lines_removed = int(part.split()[0])
        return full_diff_output, lines_added, lines_removed
    except FileNotFoundError:
        # This case is handled by the caller checking os.path.exists for original_file_abs_in_repo_state
        # If patched_file_abs is missing, it's also handled earlier.
        # If file1_path (original) is not found for diff, it implies CREATED scenario.
        # If file2_path (patched) is not found (should not happen due to earlier checks).
        # Returning empty diff and 0,0; the 'CREATED' status logic will handle line counts.
        return "", 0, 0 
    except Exception as e:
        print(f"Error getting diff output and stats for {file1_path} vs {file2_path}: {e}")
        return "", 0, 0 # Return empty diff and 0,0 for stats if unexpected error

def analyze_bounty_patch(bounty_id: str, base_bountybench_dir: str) -> Dict[str, Any]:
    """Analyzes patch files for a single bounty."""
    bounty_parts = bounty_id.rsplit('_', 1)
    repo_name = bounty_parts[0]
    bounty_num_str = bounty_parts[1]

    bounty_dir = os.path.join(base_bountybench_dir, repo_name, "bounties", f"bounty_{bounty_num_str}")
    metadata_path = os.path.join(bounty_dir, "bounty_metadata.json")
    codebase_dir = os.path.join(base_bountybench_dir, repo_name, "codebase")

    stats = {
        "bounty_id": bounty_id,
        "total_lines_added": 0,
        "total_lines_removed": 0,
        "files_created": 0,
        "files_deleted": 0,  # Per user request, this will remain 0
        "files_modified": 0,
        "patch_details": [],
        "diff_file_path": "",
        "error_log": [] 
    }

    def log_error(message):
        print(f"Error for {bounty_id}: {message}")
        stats["error_log"].append(message)

    if not os.path.exists(metadata_path):
        log_error(f"bounty_metadata.json not found at {metadata_path}")
        return stats
    if not os.path.isdir(codebase_dir):
        log_error(f"Codebase directory not found at {codebase_dir}")
        return stats

    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    except Exception as e:
        log_error(f"Error reading metadata {metadata_path}: {str(e)}")
        return stats

    vulnerable_commit = metadata.get("vulnerable_commit")
    patch_data = metadata.get("patch")

    if not vulnerable_commit:
        log_error("vulnerable_commit not found in metadata.")
        # Continue if patch_data exists, to at least report patch files as 'created'
    if not patch_data or not isinstance(patch_data, dict):
        log_error("Patch data not found or invalid in metadata.")
        return stats

    original_git_state = None
    original_git_state = None
    all_diffs_for_bounty = [] # To store diff strings for each file in the bounty
    try:
        original_git_state = get_current_git_state(codebase_dir)
        print(f"Original state for {codebase_dir}: {original_git_state}")
        
        if vulnerable_commit:
             checkout_git_state(codebase_dir, vulnerable_commit)
        else: # No vulnerable_commit, assume all patch files are new relative to current state (less accurate)
            log_error("No vulnerable_commit, patch stats might be inaccurate, assuming current state as base.")

        for patched_file_rel_bounty, original_file_rel_repo_root in patch_data.items():
            patched_file_abs = os.path.join(bounty_dir, patched_file_rel_bounty)
            
            # Determine path relative to codebase_dir
            # Example: value is "codebase/src/file.py", codebase_dir is ".../repo/codebase" -> we need "src/file.py"
            if original_file_rel_repo_root.startswith("codebase" + os.sep):
                original_file_in_codebase_rel = original_file_rel_repo_root[len("codebase" + os.sep):]
            else:
                original_file_in_codebase_rel = original_file_rel_repo_root
            
            original_file_abs_in_repo_state = os.path.join(codebase_dir, original_file_in_codebase_rel)

            file_stat = {
                "patched_file_bounty_path": patched_file_rel_bounty,
                "original_file_repo_path": original_file_rel_repo_root,
                "original_file_codebase_relative_path": original_file_in_codebase_rel,
                "status": "", "lines_added": 0, "lines_removed": 0
            }

            if not os.path.exists(patched_file_abs):
                file_stat["status"] = "PATCH_FILE_MISSING"
                log_error(f"Patched file {patched_file_abs} not found.")
                stats["patch_details"].append(file_stat)
                continue
            
            # If vulnerable_commit was not available, or original file doesn't exist there: it's CREATED
            file_diff_content = ""
            if not vulnerable_commit or not os.path.exists(original_file_abs_in_repo_state):
                file_stat["status"] = "CREATED"
                added = count_non_blank_lines(patched_file_abs)
                removed = 0 # By definition for a new file
                stats["files_created"] += 1
                # Generate a diff-like output for created file (content of new file)
                try:
                    with open(patched_file_abs, 'r', encoding='utf-8', errors='ignore') as pf_content:
                        file_diff_content = f"--- /dev/null\n+++ {original_file_in_codebase_rel}\n" + ''.join([f"+{line}" for line in pf_content])
                except Exception as e_read:
                    log_error(f"Could not read created file {patched_file_abs} for diff: {e_read}")
                    file_diff_content = f"Error reading created file {patched_file_abs}\n"
            else: # Original file exists in the checked-out state, so it's MODIFIED
                file_stat["status"] = "MODIFIED"
                diff_out, added, removed = get_diff_output_and_stats(original_file_abs_in_repo_state, patched_file_abs)
                file_diff_content = diff_out
                if added > 0 or removed > 0 or (diff_out and "Binary files" in diff_out) :
                    stats["files_modified"] += 1
            
            all_diffs_for_bounty.append(f"Diff for {patched_file_rel_bounty} vs {original_file_rel_repo_root}:\n{file_diff_content}\n")

            
            file_stat["lines_added"] = added
            file_stat["lines_removed"] = removed
            stats["total_lines_added"] += added
            stats["total_lines_removed"] += removed
            stats["patch_details"].append(file_stat)

    except subprocess.CalledProcessError as e:
        log_error(f"Git command failed: {e.cmd} - {e.stderr}. Bounty {bounty_id} might be incomplete.")
    except Exception as e:
        log_error(f"General error analyzing {bounty_id}: {str(e)}. Bounty might be incomplete.")
    finally:
        if original_git_state and os.path.isdir(codebase_dir):
            try:
                print(f"Restoring {codebase_dir} to {original_git_state}...")
                checkout_git_state(codebase_dir, original_git_state, force_clean=True)
            except Exception as e_checkout:
                log_error(f"CRITICAL: Failed to restore {codebase_dir} to '{original_git_state}': {str(e_checkout)}")
        elif not os.path.isdir(codebase_dir):
             log_error(f"CRITICAL: Codebase dir {codebase_dir} not found for Git restoration.")
        elif not original_git_state:
            log_error(f"Warning: Original Git state for {codebase_dir} was not captured, cannot restore automatically.")

    # After processing all files for the bounty, save the combined diffs
    if all_diffs_for_bounty:
        if not os.path.exists(PATCH_DIFFS_DIR):
            try:
                os.makedirs(PATCH_DIFFS_DIR)
            except Exception as e_mkdir:
                log_error(f"Failed to create patch diffs directory {PATCH_DIFFS_DIR}: {e_mkdir}")
                return stats # Cannot save diff file
        
        bounty_diff_filename = f"{bounty_id.replace('/', '_')}_patch.diff"
        bounty_diff_filepath = os.path.join(PATCH_DIFFS_DIR, bounty_diff_filename)
        try:
            with open(bounty_diff_filepath, 'w', encoding='utf-8') as df:
                df.write(f"== {bounty_id} ==\n\n")
                df.write("\n\n".join(all_diffs_for_bounty))
            stats["diff_file_path"] = os.path.join("patch_diffs", bounty_diff_filename) # Store relative path
        except Exception as e_write_diff:
            log_error(f"Failed to write diff file {bounty_diff_filepath}: {e_write_diff}")
    
    return stats

def main():
    all_bounty_stats = {}
    base_bountybench_dir = BASE_DIR_BOUNTYBENCH
    bounties_to_process = BOUNTIES

    # Create patch_diffs directory if it doesn't exist
    if not os.path.exists(PATCH_DIFFS_DIR):
        try:
            os.makedirs(PATCH_DIFFS_DIR)
            print(f"Created directory for patch diffs: {PATCH_DIFFS_DIR}")
        except Exception as e:
            print(f"Error creating patch diffs directory {PATCH_DIFFS_DIR}: {e}. Diff files may not be saved.")
            # Proceed, but diffs won't be saved if dir creation fails later for a specific bounty

    for bounty_id in bounties_to_process:
        print(f"\n--- Processing bounty: {bounty_id} ---")
        bounty_stat = analyze_bounty_patch(bounty_id, base_bountybench_dir)
        all_bounty_stats[bounty_id] = bounty_stat

    sorted_bounty_stats = {k: all_bounty_stats[k] for k in sorted(all_bounty_stats.keys())}

    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(sorted_bounty_stats, f, indent=2)
        print(f"\nAnalysis complete. Results saved to {OUTPUT_FILE}")
    except Exception as e:
        print(f"Error writing output JSON to {OUTPUT_FILE}: {str(e)}")

    print("\nSummary of Patch Stats (from analyze_patch_stats.py):")
    header = f"{'Bounty ID':<20} | {'Files Created':<13} | {'Files Modified':<14} | {'Lines Added':<11} | {'Lines Removed':<13} | {'Errors?':<7}"
    print(header)
    print("-" * len(header))
    for bounty_id, data in sorted_bounty_stats.items():
        error_present = "Yes" if data.get('error_log') else "No"
        print(f"{bounty_id:<20} | {data.get('files_created', 0):<13} | {data.get('files_modified', 0):<14} | {data.get('total_lines_added', 0):<11} | {data.get('total_lines_removed', 0):<13} | {error_present:<7}")

if __name__ == "__main__":
    main()
