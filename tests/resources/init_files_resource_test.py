import os
import subprocess
import unittest
import logging

from resources.init_files_resource import InitFilesResource  # Adjust import based on your structure

# Configure logging
logging.basicConfig(level=logging.INFO)

class TestInitFilesResource(unittest.TestCase):
    def test_setup_repo(self):
        self.task_repo_dir = os.path.join(os.getcwd(), "tests", "resources", "file_tests")
        self.tmp_dir = "tmp_dir_for_testing"

        # Set up InitFilesResource
        self.resource = InitFilesResource(self.task_repo_dir, self.tmp_dir)

        # Test if the repository is initialized correctly.
        repo_path = os.path.join(self.task_repo_dir, "original_files")
        git_dir = os.path.join(repo_path, ".git")
        
        # Check if .git directory exists
        self.assertTrue(os.path.exists(git_dir), "Git repository was not initialized.")
        
        # Check if the initial commit was made
        result = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=repo_path, stdout=subprocess.PIPE, text=True)
        self.assertEqual(result.stdout.strip(), "1", "Initial commit not found.")

        dev_branch = subprocess.run(["git", "status"], cwd=repo_path, stdout=subprocess.PIPE, text=True)
        self.assertIn("On branch dev", dev_branch.stdout, "Not in dev branch")

        self.resource.stop()
        self.assertFalse(os.path.exists(git_dir))
        self.assertFalse(os.path.exists(self.tmp_dir))

if __name__ == '__main__':
    unittest.main()
