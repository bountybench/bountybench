import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import unittest
from fastapi.testclient import TestClient
from backend.main import create_app
from unittest import IsolatedAsyncioTestCase



from tests.ui_backend.fake_workflows import (FakeDetectWorkflow, FakeExploitAndPatchWorkflow,
                                    FakePatchWorkflow,
                                    FakeChatWorkflow
)



class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Equivalent to the pytest fixture that creates the app and client once per test class.
        """
        # Create a fake workflow factory just like in conftest.py
        cls.fake_workflow_factory = {
            "Detect Workflow":    FakeDetectWorkflow, 
            "Exploit and Patch Workflow": FakeExploitAndPatchWorkflow,  
            "Patch Workflow":     FakePatchWorkflow,  
            "Chat Workflow":      FakeChatWorkflow,  
        }
        # Create the FastAPI app using your create_app function
        cls.app = create_app(workflow_factory=cls.fake_workflow_factory)
        # Create a TestClient for synchronous testing
        cls.client = TestClient(cls.app)

    def test_list_workflows(self):
        """
        Test the /workflow/list endpoint to ensure it returns the correct list of workflows.
        """
        response = self.client.get("/workflow/list")
        self.assertEqual(response.status_code, 200, "Expected status code 200")
        data = response.json()
        self.assertIn("workflows", data, "Response should contain 'workflows' key")
        self.assertIsInstance(data["workflows"], list, "'workflows' should be a list")
        self.assertEqual(len(data["workflows"]), 4, "There should be exactly 4 workflows listed")

        expected_ids = {"detect", "exploit_and_patch", "patch", "chat"}
        returned_ids = {wf["id"] for wf in data["workflows"]}
        self.assertEqual(returned_ids, expected_ids, "Workflow IDs do not match expected IDs")

    def test_start_workflow_success(self):
        """
        Test starting a workflow with valid data.
        """
        payload = {
            "workflow_name": "Detect Workflow",
            "task_dir": "/path/to/tasks",
            "bounty_number": "123",
            "interactive": True,
            "iterations": 5
        }
        response = self.client.post("/workflow/start", json=payload)
        self.assertEqual(response.status_code, 200, "Expected status code 200")
        data = response.json()
        self.assertIn("workflow_id", data, "Response should contain 'workflow_id'")
        self.assertIn("status", data, "Response should contain 'status'")
        self.assertEqual(data["status"], "initializing", "Status should be 'initializing'")
        self.assertEqual(data["workflow_id"], "fake-123", "Workflow ID does not match expected fake ID")

    def test_start_workflow_invalid_name(self):
        """
        Test starting a workflow with an invalid workflow name.
        """
        payload = {
            "workflow_name": "Unknown Workflow",
            "task_dir": "/path/to/tasks",
            "bounty_number": "123",
            "interactive": True,
            "iterations": 5
        }
        response = self.client.post("/workflow/start", json=payload)
        # As per server.py, it returns 200 even on error
        self.assertEqual(response.status_code, 200, "Expected status code 200 even on error")
        data = response.json()
        self.assertIn("error", data, "Response should contain 'error' key")
        self.assertIn("Unknown Workflow", data["error"], "Error message should indicate unknown workflow")

    def test_next_message_success(self):
        """
        Test retrieving the next message in an existing workflow.
        """
        start_payload = {
            "workflow_name": "Chat Workflow",
            "task_dir": "/path/to/tasks",
            "bounty_number": "456",
            "interactive": True,
            "iterations": 2
        }
        start_response = self.client.post("/workflow/start", json=start_payload)
        self.assertEqual(start_response.status_code, 200, "Expected status code 200 for start workflow")
        workflow_id = start_response.json()["workflow_id"]

        response = self.client.post(f"/workflow/next/{workflow_id}")
        self.assertEqual(response.status_code, 200, "Expected status code 200 for next message")
        data = response.json()
        self.assertIn("status", data, "Response should contain 'status'")
        self.assertEqual(data["status"], "updated", "Status should be 'updated'")
        self.assertIn("result", data, "Response should contain 'result'")
        self.assertEqual(data["result"], "fake-message-id", "Result ID does not match expected fake message ID")

    def test_next_message_workflow_not_found(self):
        """
        Test retrieving the next message for a non-existent workflow.
        """
        response = self.client.post("/workflow/next/nonexistent-id")
        self.assertEqual(response.status_code, 200, "Expected status code 200 even on error")
        data = response.json()
        self.assertIn("error", data, "Response should contain 'error' key")
        self.assertEqual(data["error"], "Workflow nonexistent-id not found",
                         "Error message should indicate workflow not found")

    def test_rerun_message_success(self):
        """
        Test rerunning a message in an existing workflow.
        """
        start_payload = {
            "workflow_name": "Patch Workflow",
            "task_dir": "/path/to/tasks",
            "bounty_number": "789",
            "interactive": False,
            "iterations": 1
        }
        start_response = self.client.post("/workflow/start", json=start_payload)
        self.assertEqual(start_response.status_code, 200, "Expected status code 200 for start workflow")
        workflow_id = start_response.json()["workflow_id"]

        payload = {"message_id": "original-message-id"}
        response = self.client.post(f"/workflow/rerun-message/{workflow_id}", json=payload)
        self.assertEqual(response.status_code, 200, "Expected status code 200 for rerun message")
        data = response.json()
        self.assertIn("status", data, "Response should contain 'status'")
        self.assertEqual(data["status"], "updated", "Status should be 'updated'")
        self.assertIn("result", data, "Response should contain 'result'")
        self.assertEqual(data["result"], "fake-rerun-message-id",
                         "Result ID does not match expected fake rerun message ID")

    def test_rerun_message_workflow_not_found(self):
        """
        Test rerunning a message in a non-existent workflow.
        """
        payload = {"message_id": "some-id"}
        response = self.client.post("/workflow/rerun-message/nonexistent-id", json=payload)
        self.assertEqual(response.status_code, 200, "Expected status code 200 even on error")
        data = response.json()
        self.assertIn("error", data, "Response should contain 'error' key")
        self.assertEqual(data["error"], "Workflow nonexistent-id not found",
                         "Error message should indicate workflow not found")

    def test_edit_action_input_success(self):
        """
        Test editing an action input in an existing workflow.
        """
        start_payload = {
            "workflow_name": "Chat Workflow",
            "task_dir": "/path/to/tasks",
            "bounty_number": "321",
            "interactive": True,
            "iterations": 4
        }
        start_response = self.client.post("/workflow/start", json=start_payload)
        self.assertEqual(start_response.status_code, 200, "Expected status code 200 for start workflow")
        workflow_id = start_response.json()["workflow_id"]

        payload = {
            "message_id": "msg-123",
            "new_input_data": "Updated input data"
        }
        response = self.client.post(f"/workflow/edit-message/{workflow_id}", json=payload)
        self.assertEqual(response.status_code, 200, "Expected status code 200 for edit message")
        data = response.json()
        self.assertIn("status", data, "Response should contain 'status'")
        self.assertEqual(data["status"], "updated", "Status should be 'updated'")
        self.assertIn("result", data, "Response should contain 'result'")
        self.assertEqual(data["result"], "fake-edited-message-id",
                         "Result ID does not match expected fake edited message ID")

    def test_edit_action_input_workflow_not_found(self):
        """
        Test editing an action input in a non-existent workflow.
        """
        payload = {
            "message_id": "msg-123",
            "new_input_data": "Updated input data"
        }
        response = self.client.post("/workflow/edit-message/nonexistent-id", json=payload)
        self.assertEqual(response.status_code, 200, "Expected status code 200 even on error")
        data = response.json()
        self.assertIn("error", data, "Response should contain 'error' key")
        self.assertEqual(data["error"], "Workflow nonexistent-id not found",
                         "Error message should indicate workflow not found")

    def test_update_interactive_mode_success(self):
        """
        Test updating the interactive mode of an existing workflow.
        """
        start_payload = {
            "workflow_name": "Detect Workflow",
            "task_dir": "/path/to/tasks",
            "bounty_number": "654",
            "interactive": False,
            "iterations": 2
        }
        start_response = self.client.post("/workflow/start", json=start_payload)
        self.assertEqual(start_response.status_code, 200, "Expected status code 200 for start workflow")
        workflow_id = start_response.json()["workflow_id"]

        payload = {"interactive": True}
        response = self.client.post(f"/workflow/{workflow_id}/interactive", json=payload)
        self.assertEqual(response.status_code, 200, "Expected status code 200 for updating interactive mode")
        data = response.json()
        self.assertIn("status", data, "Response should contain 'status'")
        self.assertEqual(data["status"], "success", "Status should be 'success'")
        self.assertIn("interactive", data, "Response should contain 'interactive'")
        self.assertTrue(data["interactive"], "Interactive mode should be updated to True")

    def test_update_interactive_mode_missing_field(self):
        """
        Test updating the interactive mode without providing the required field.
        """
        start_payload = {
            "workflow_name": "Detect Workflow",
            "task_dir": "/path/to/tasks",
            "bounty_number": "654",
            "interactive": False,
            "iterations": 2
        }
        start_response = self.client.post("/workflow/start", json=start_payload)
        self.assertEqual(start_response.status_code, 200, "Expected status code 200 for start workflow")
        workflow_id = start_response.json()["workflow_id"]

        payload = {}
        response = self.client.post(f"/workflow/{workflow_id}/interactive", json=payload)
        self.assertEqual(response.status_code, 422, "Expected status code 422 for missing 'interactive' field")
        data = response.json()
        self.assertIn("detail", data, "Response should contain 'detail' key")
        self.assertEqual(len(data["detail"]), 1, "There should be one error")
        error = data["detail"][0]
        self.assertEqual(error["type"], "missing", "Error type should be 'missing'")
        self.assertEqual(error["loc"], ["body", "interactive"], "Error location should point to 'interactive' field")

    def test_last_message_success(self):
        """
        Test retrieving the last message of an existing workflow.
        """
        start_payload = {
            "workflow_name": "Chat Workflow",
            "task_dir": "/path/to/tasks",
            "bounty_number": "987",
            "interactive": True,
            "iterations": 3
        }
        start_response = self.client.post("/workflow/start", json=start_payload)
        self.assertEqual(start_response.status_code, 200, "Expected status code 200 for start workflow")
        workflow_id = start_response.json()["workflow_id"]

        response = self.client.get(f"/workflow/last-message/{workflow_id}")
        self.assertEqual(response.status_code, 200, "Expected status code 200 for last message")
        data = response.json()
        self.assertIn("message_type", data, "Response should contain 'message_type'")
        self.assertEqual(data["message_type"], "last_message", "Message type should be 'last_message'")
        self.assertIn("content", data, "Response should contain 'content'")
        self.assertEqual(data["content"], "This is the last fake message.",
                         "Content does not match expected fake last message")

    def test_last_message_workflow_not_found(self):
        """
        Test retrieving the last message of a non-existent workflow.
        """
        response = self.client.get("/workflow/last-message/nonexistent-id")
        self.assertEqual(response.status_code, 200, "Expected status code 200 even on error")
        data = response.json()
        self.assertIn("error", data, "Response should contain 'error' key")
        self.assertEqual(data["error"], "Workflow not found", "Error message should indicate workflow not found")

    def test_start_workflow_missing_fields(self):
        """
        Test starting a workflow with missing required fields.
        """
        payload = {
            "workflow_name": "Detect Workflow",
            # "task_dir" is missing
            "bounty_number": "123",
            "interactive": True,
            "iterations": 5
        }
        response = self.client.post("/workflow/start", json=payload)
        self.assertEqual(response.status_code, 422, "Expected status code 422 for validation error")
        data = response.json()
        self.assertIn("detail", data, "Response should contain 'detail' key")

    def test_edit_action_input_invalid_payload(self):
        """
        Test editing an action input with invalid payload data.
        """
        start_payload = {
            "workflow_name": "Chat Workflow",
            "task_dir": "/path/to/tasks",
            "bounty_number": "321",
            "interactive": True,
            "iterations": 4
        }
        start_response = self.client.post("/workflow/start", json=start_payload)
        workflow_id = start_response.json()["workflow_id"]

        # Missing 'new_input_data'
        payload = {
            "message_id": "msg-123"
        }
        response = self.client.post(f"/workflow/edit-message/{workflow_id}", json=payload)
        self.assertEqual(response.status_code, 422, "Expected status code 422 for validation error")
        data = response.json()
        self.assertIn("detail", data, "Response should contain 'detail' key")

    def test_update_interactive_mode_invalid_payload(self):
        """
        Test updating interactive mode with invalid payload data.
        """
        start_payload = {
            "workflow_name": "Detect Workflow",
            "task_dir": "/path/to/tasks",
            "bounty_number": "654",
            "interactive": False,
            "iterations": 2
        }
        start_response = self.client.post("/workflow/start", json=start_payload)
        workflow_id = start_response.json()["workflow_id"]

        # Send invalid payload (non-boolean 'interactive' field)
        payload = {"interactive": "random"}
        response = self.client.post(f"/workflow/{workflow_id}/interactive", json=payload)
        self.assertEqual(response.status_code, 422, "Expected status code 422 for type validation error")
        data = response.json()
        self.assertEqual(len(data['detail']), 1, "Expected one error in the response")
        error = data['detail'][0]
        self.assertEqual(error['type'], 'bool_parsing', f"Expected error type 'bool_parsing'")
        self.assertEqual(error['loc'], ['body', 'interactive'], "Error should be located in body.interactive")
        self.assertIn("Input should be a valid boolean", error['msg'], "Error message should indicate invalid boolean")
        self.assertEqual(error['input'], 'random', "Error should include the invalid input")

    def test_workflow_restart_creates_new_workflow(self):
        """
        Test that stopping a workflow does not remove it from active workflows, 
        and starting a new workflow creates a new instance with a different ID.
        """
        start_payload = {
            "workflow_name": "Exploit and Patch Workflow",
            "task_dir": "/path/to/tasks",
            "bounty_number": "999",
            "interactive": True,
            "iterations": 3
        }

        new_payload = {
            "workflow_name": "Exploit and Patch Workflow",
            "task_dir": "/path/to/tasks",
            "bounty_number": "100",
            "interactive": True,
            "iterations": 3
        }

        # Step 1: Start the first workflow
        start_response_1 = self.client.post("/workflow/start", json=start_payload)
        self.assertEqual(start_response_1.status_code, 200, "Expected status code 200 for first workflow start")
        workflow_id_1 = start_response_1.json()["workflow_id"]

        # Step 2: Stop the first workflow
        stop_response = self.client.post(f"/workflow/stop/{workflow_id_1}")
        self.assertEqual(stop_response.status_code, 200, "Expected status code 200 for stopping workflow")
        self.assertIn("status", stop_response.json(), "Response should contain 'status'")
        self.assertEqual(stop_response.json()["status"], "stopped", "Workflow should be marked as stopped")

        # Step 3: Verify that the stopped workflow still exists in active workflows
        active_workflows_before_restart = self.client.get("/workflows/active").json()
        found_workflow = next((w for w in active_workflows_before_restart["active_workflows"] if w["id"] == workflow_id_1), None)
        self.assertIsNotNone(found_workflow, "Stopped workflow should still be in active workflows")
        self.assertEqual(found_workflow["status"], "stopped", "Stopped workflow should have status 'stopped'")

        # Step 4: Start a new workflow
        start_response_2 = self.client.post("/workflow/start", json=new_payload)
        self.assertEqual(start_response_2.status_code, 200, "Expected status code 200 for second workflow start")
        workflow_id_2 = start_response_2.json()["workflow_id"]

        # Step 5: Ensure the new workflow ID is different
        self.assertNotEqual(workflow_id_1, workflow_id_2, "New workflow should have a different ID")

        # Step 6: Ensure both workflows exist in active workflows
        active_workflows_after_restart = self.client.get("/workflows/active").json()
        workflow_ids = {w["id"] for w in active_workflows_after_restart["active_workflows"]}

        self.assertIn(workflow_id_1, workflow_ids, "Old workflow should still exist")
        self.assertIn(workflow_id_2, workflow_ids, "New workflow should be added")
        
        # Step 7: Ensure the old workflow is still stopped and the new workflow is initializing
        old_workflow = next((w for w in active_workflows_after_restart["active_workflows"] if w["id"] == workflow_id_1), None)
        new_workflow = next((w for w in active_workflows_after_restart["active_workflows"] if w["id"] == workflow_id_2), None)

        self.assertEqual(old_workflow["status"], "stopped", "Old workflow should remain stopped")
        self.assertEqual(new_workflow["status"], "initializing", "New workflow should be in 'initializing' state")


    def test_stopping_multiple_workflows(self):
        """
        Test that stopping multiple workflows correctly updates their statuses to 'stopped'
        while keeping them in active workflows.
        """
        start_payload_1 = {
            "workflow_name": "Exploit and Patch Workflow",
            "task_dir": "/path/to/tasks",
            "bounty_number": "101",
            "interactive": True,
            "iterations": 3
        }

        start_payload_2 = {
            "workflow_name": "Detect Workflow",
            "task_dir": "/path/to/tasks",
            "bounty_number": "102",
            "interactive": True,
            "iterations": 3
        }

        # Start two workflows
        start_response_1 = self.client.post("/workflow/start", json=start_payload_1)
        workflow_id_1 = start_response_1.json()["workflow_id"]

        start_response_2 = self.client.post("/workflow/start", json=start_payload_2)
        workflow_id_2 = start_response_2.json()["workflow_id"]

        # Stop both workflows
        stop_response_1 = self.client.post(f"/workflow/stop/{workflow_id_1}")
        stop_response_2 = self.client.post(f"/workflow/stop/{workflow_id_2}")

        self.assertEqual(stop_response_1.status_code, 200, "Expected status code 200 for stopping first workflow")
        self.assertEqual(stop_response_2.status_code, 200, "Expected status code 200 for stopping second workflow")

        # Verify that both workflows still exist but are marked as 'stopped'
        active_workflows = self.client.get("/workflows/active").json()
        workflow_1_status = next(w["status"] for w in active_workflows["active_workflows"] if w["id"] == workflow_id_1)
        workflow_2_status = next(w["status"] for w in active_workflows["active_workflows"] if w["id"] == workflow_id_2)

        self.assertEqual(workflow_1_status, "stopped", "First workflow should be marked as stopped")
        self.assertEqual(workflow_2_status, "stopped", "Second workflow should be marked as stopped")

    def test_restarting_workflow_with_same_bounty_number(self):
        """
        Test that stopping a workflow and restarting it with the same bounty number does not overwrite the original workflow.
        """
        start_payload = {
            "workflow_name": "Exploit and Patch Workflow",
            "task_dir": "/path/to/tasks",
            "bounty_number": "999",
            "interactive": True,
            "iterations": 3
        }

        # Start the first workflow
        start_response_1 = self.client.post("/workflow/start", json=start_payload)
        workflow_id_1 = start_response_1.json()["workflow_id"]

        # Stop the first workflow
        stop_response = self.client.post(f"/workflow/stop/{workflow_id_1}")
        self.assertEqual(stop_response.status_code, 200, "Expected status code 200 for stopping workflow")

        # Restart with the same bounty number
        start_response_2 = self.client.post("/workflow/start", json=start_payload)
        workflow_id_2 = start_response_2.json()["workflow_id"]

        self.assertEqual(workflow_id_1, workflow_id_2, "New workflow should have same ID  with the same bounty number")

    def test_stopping_workflow_twice(self):
        """
        Test that stopping a workflow twice does not cause errors and does not change its status after the first stop.
        """
        start_payload = {
            "workflow_name": "Patch Workflow",
            "task_dir": "/path/to/tasks",
            "bounty_number": "777",
            "interactive": True,
            "iterations": 3
        }

        # Start the workflow
        start_response = self.client.post("/workflow/start", json=start_payload)
        workflow_id = start_response.json()["workflow_id"]

        # Stop the workflow once
        stop_response_1 = self.client.post(f"/workflow/stop/{workflow_id}")
        self.assertEqual(stop_response_1.status_code, 200, "Expected status code 200 for stopping workflow the first time")
        
        # Stop the workflow again
        stop_response_2 = self.client.post(f"/workflow/stop/{workflow_id}")
        self.assertEqual(stop_response_2.status_code, 200, "Expected status code 200 even for repeated stop")

        # Verify that the workflow is still present in active workflows with 'stopped' status
        active_workflows = self.client.get("/workflows/active").json()
        workflow_status = next(w["status"] for w in active_workflows["active_workflows"] if w["id"] == workflow_id)

        self.assertEqual(workflow_status, "stopped", "Workflow should still be in 'stopped' status")



###############################################################################
# ASYNC TESTS
###############################################################################
class TestWebsocket(IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        """
        Setup for async websocket tests. Similar approach as above.
        """
        cls.fake_workflow_factory = {
                "Detect Workflow":    FakeDetectWorkflow, 
                "Exploit and Patch Workflow": FakeExploitAndPatchWorkflow,  
                "Patch Workflow":     FakePatchWorkflow,  
                "Chat Workflow":      FakeChatWorkflow,  
        }
        cls.app = create_app(workflow_factory=cls.fake_workflow_factory)
        cls.client = TestClient(cls.app)

    async def asyncSetUp(self):
        """
        Called before each async test. If you need to start a workflow or mutate
        state for each test, you can do it here or in the test itself.
        """
        pass

    async def test_websocket_connection_success(self):
        """
        Tests connecting to a workflow via websocket.
        """
        # Setup a known workflow so that /ws/{workflow_id} is valid.
        # For example, simulate the same logic as your pytest fixture:
        workflow_id = "fake-123"
        start_payload = {
            "workflow_name": "Detect Workflow",
            "task_dir": "/path/to/tasks",
            "bounty_number": "123",
            "interactive": True,
            "iterations": 5
        }
        start_response = self.client.post("/workflow/start", json=start_payload)
        self.assertEqual(start_response.status_code, 200)
        data = start_response.json()
        self.assertEqual(data["workflow_id"], workflow_id)

        with self.client.websocket_connect(f"/ws/{workflow_id}") as websocket:
            initial_state = websocket.receive_json()
            self.assertEqual(initial_state["message_type"], "connection_established")
            self.assertEqual(initial_state["status"], "connected")

    async def test_websocket_receive_status_update(self):
        """
        Test receiving status updates from the websocket after connection
        """
        workflow_id = "fake-123"
        start_payload = {
            "workflow_name": "Detect Workflow",
            "task_dir": "/path/to/tasks",
            "bounty_number": "123",
            "interactive": True,
            "iterations": 5
        }
        start_response = self.client.post("/workflow/start", json=start_payload)
        self.assertEqual(start_response.status_code, 200)
        data = start_response.json()
        self.assertEqual(data["workflow_id"], workflow_id)

        with self.client.websocket_connect(f"/ws/{workflow_id}") as websocket:
            # Verify connection establishment
            connection_msg = websocket.receive_json()
            self.assertEqual(connection_msg["message_type"], "connection_established")
            self.assertEqual(connection_msg["status"], "connected")

            # Verify initial status
            status_msg = websocket.receive_json()
            self.assertEqual(status_msg["message_type"], "workflow_status")
            self.assertEqual(status_msg["status"], "initializing")

            # Verify progression to running state
            running_msg = websocket.receive_json()
            self.assertEqual(running_msg["message_type"], "workflow_status")
            self.assertEqual(running_msg["status"], "running")