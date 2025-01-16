import os
import subprocess
import unittest
import logging
import shutil

from resources.init_files_resource import InitFilesResource, InitFilesResourceConfig

# Configure logging
logging.basicConfig(level=logging.INFO)

class TestInitFilesResource(unittest.TestCase):
    def setUp(self):
        # Define directory paths
        self.task_repo_dir = os.path.join(os.getcwd(), "tests", "resources", "test_files")
        self.tmp_dir_name = "tmp_dir_for_testing"
        self.tmp_dir = os.path.join(self.task_repo_dir, self.tmp_dir_name)
        self.original_files_dir = os.path.join(self.task_repo_dir, "original_files")

        # Clean up directories before testing
        if os.path.exists(self.task_repo_dir):
            shutil.rmtree(self.task_repo_dir)
        os.makedirs(self.original_files_dir, exist_ok=True)

        # Create a test file in the original_files directory
        with open(os.path.join(self.original_files_dir, "test_file.txt"), "w") as f:
            f.write("This is a test.")

        # Initialize the original_files directory as a git repository and make an initial commit
        subprocess.run(["git", "init"], cwd=self.original_files_dir)
        subprocess.run(["git", "add", "."], cwd=self.original_files_dir)
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=self.original_files_dir)
        subprocess.run(["git", "branch", "-m", "main"], cwd=self.original_files_dir)

        # Configuration for InitFilesResource
        self.config = InitFilesResourceConfig(
            task_dir=self.task_repo_dir,
            files_dir_name="original_files",
            tmp_dir_name=self.tmp_dir_name,
            bounty_number="1234",
            vulnerable_commit="HEAD"
        )

    def tearDown(self):
        if os.path.exists(self.task_repo_dir):
            shutil.rmtree(self.task_repo_dir)

    def test_setup_repo(self):
        # Set up InitFilesResource
        self.resource = InitFilesResource(resource_id="test_resource", config=self.config)

        # Ensure the temporary repository is properly set up
        repo_path = os.path.join(self.tmp_dir, "original_files")
        git_dir = os.path.join(repo_path, ".git")

        # Check if the .git directory exists
        self.assertTrue(os.path.exists(git_dir), "Git repository was not initialized.")

        # Check if an initial commit was made
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"], 
            cwd=repo_path, stdout=subprocess.PIPE, text=True
        )
        self.assertEqual(result.stdout.strip(), "1", "Initial commit not found.")

    def test_setup_dev_branch(self):
        # Set up InitFilesResource
        self.resource = InitFilesResource(resource_id="test_resource", config=self.config)

        # Invoke the setup_dev_branch method directly
        self.resource.setup_dev_branch(self.original_files_dir)

        # Verify that the branch was created and switched to 'dev'
        result = subprocess.run(["git", "branch"], cwd=self.original_files_dir, stdout=subprocess.PIPE, text=True)
        self.assertIn("dev", result.stdout, "Branch 'dev' was not created.")

        current_branch = subprocess.run(["git", "status"], cwd=self.original_files_dir, stdout=subprocess.PIPE, text=True)
        self.assertIn("On branch dev", current_branch.stdout, "Repository is not on branch 'dev'")

    def test_stop(self):
        # Set up InitFilesResource
        self.resource = InitFilesResource(resource_id="test_resource", config=self.config)

        # Create a 'dev' branch
        repo_path = os.path.join(self.tmp_dir, "original_files")
        subprocess.run(["git", "checkout", "-b", "dev"], cwd=repo_path)

        # Stop the resource and assert cleanup
        self.resource.stop()

        # Verify temporary directory removal
        self.assertFalse(os.path.exists(self.tmp_dir))

        # Verify 'dev' branch removal from the original repo
        branch_result = subprocess.run(["git", "branch"], cwd=self.original_files_dir, stdout=subprocess.PIPE, text=True)
        self.assertNotIn("dev", branch_result.stdout, "Branch 'dev' was not removed.")

    def test_remove_tmp(self):
        # Create additional files and directories for testing
        os.makedirs(os.path.join(self.tmp_dir, "subdir"), exist_ok=True)
        with open(os.path.join(self.tmp_dir, "subdir", "tempfile.txt"), "w") as f:
            f.write("Temporary file")

        # Ensure files exist
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, "subdir", "tempfile.txt")))

        # Remove temporary directory
        self.resource = InitFilesResource(resource_id="test_resource", config=self.config)
        self.resource.remove_tmp()

        # Verify removal
        self.assertFalse(os.path.exists(self.tmp_dir))

    def test_safe_remove(self):
        # Test removing a regular file
        test_file_path = os.path.join(self.tmp_dir, "testfile.txt")
        os.makedirs(self.tmp_dir, exist_ok=True)
        with open(test_file_path, "w") as f:
            f.write("This is a test file")

        self.resource = InitFilesResource(resource_id="test_resource", config=self.config)
        self.resource.safe_remove(test_file_path)

        # Verify removal
        self.assertFalse(os.path.exists(test_file_path))

        # Test removing a directory
        test_dir_path = os.path.join(self.tmp_dir, "testdir")
        os.makedirs(test_dir_path, exist_ok=True)
        self.resource.safe_remove(test_dir_path)

        # Verify removal
        self.assertFalse(os.path.exists(test_dir_path))

if __name__ == '__main__':
    unittest.main()
