import pytest
from fastapi.testclient import TestClient
import sys
import os


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import create_app
from tests.fakes import (
    FakeWebSocketManager,
    FakeDetectWorkflow,
    FakeExploitAndPatchWorkflow,
    FakePatchWorkflow,
    FakeChatWorkflow
)
from typing import Dict, Callable

@pytest.fixture
def fake_websocket_manager():
    return FakeWebSocketManager()

@pytest.fixture
def fake_workflow_factory():
    return {
        "Detect Workflow": FakeDetectWorkflow,
        "Exploit and Patch Workflow": FakeExploitAndPatchWorkflow,
        "Patch Workflow": FakePatchWorkflow,
        "Chat Workflow": FakeChatWorkflow
    }

@pytest.fixture
def app(fake_websocket_manager, fake_workflow_factory):
    print("Creating FastAPI app")

    app = create_app(ws_manager=fake_websocket_manager, workflow_factory=fake_workflow_factory)

    print("FastAPI app created")

    return app

@pytest.fixture
def client(app):
    print("Creating TestClient")
    client = TestClient(app)
    print("TestClient created")
    return client


@pytest.fixture
def client_fixture(client: TestClient):
    """
    Fixture to provide the TestClient to the tests.
    """
    return client

