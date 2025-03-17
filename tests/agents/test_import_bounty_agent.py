import json
import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from agents.import_bounty_agent.import_bounty_agent import (
    ImportBountyAgent,
    ImportBountyAgentConfig,
)
from messages.agent_messages.import_bounty_agent_message import ImportBountyMessage
from messages.agent_messages.webscraper_agent_message import WebscraperMessage


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Setup test fixtures before each test method."""
    test_bounty_dir = "test_bounties"
    os.makedirs(test_bounty_dir, exist_ok=True)
    yield
    # Cleanup
    if os.path.exists(test_bounty_dir):
        import shutil

        shutil.rmtree(test_bounty_dir)
    failed_links_file = os.path.join("reports", "hackerone_reports", "failed_links.txt")
    if os.path.exists(failed_links_file):
        os.remove(failed_links_file)


@pytest.fixture
def agent():
    """Create agent instance for tests."""
    test_bounty_dir = "test_bounties"
    agent_config = ImportBountyAgentConfig(bounty_dir=test_bounty_dir)
    return ImportBountyAgent("import_bounty_agent", agent_config=agent_config)


@patch("selenium.webdriver.Chrome")
@patch("agents.import_bounty_agent.import_bounty_agent.get_handler")
def test_download_webpage(mock_get_handler, mock_chrome, agent):
    """Test downloading webpage content."""
    # Mock Chrome driver
    mock_driver = MagicMock()
    mock_driver.page_source = "<html>Test content</html>"
    mock_chrome.return_value = mock_driver

    # Mock handler
    mock_handler = MagicMock()
    mock_get_handler.return_value = mock_handler

    bounty_link = "https://hackerone.com/reports/123456"
    website = "https://hackerone.com/reports/"

    report_dir = agent._download_webpage(bounty_link, website)

    # Verify handler methods were called
    mock_handler.wait_for_page_load.assert_called_once()
    mock_handler.scroll_to_load_content.assert_called_once()

    # Verify file was saved
    html_file = os.path.join(report_dir, "report_123456.html")
    assert os.path.exists(html_file)

    with open(html_file, "r") as f:
        assert f.read() == "<html>Test content</html>"


def test_write_bounty_metadata(agent):
    """Test writing metadata to file."""
    report_dir = os.path.join("test_bounties", "report_test")
    os.makedirs(report_dir, exist_ok=True)

    test_metadata = {
        "bounty_link": "https://test.com/123",
        "severity": "high",
        "CWE": "CWE-79",
    }

    agent._write_bounty_metadata(report_dir, test_metadata)

    metadata_file = os.path.join(report_dir, "bounty_metadata.json")
    assert os.path.exists(metadata_file)

    with open(metadata_file, "r") as f:
        saved_metadata = json.load(f)
        assert saved_metadata == test_metadata


@patch("agents.import_bounty_agent.import_bounty_agent.get_handler")
def test_extract_metadata(mock_get_handler, agent):
    """Test metadata extraction."""
    mock_handler = MagicMock()
    mock_handler.extract_metadata.return_value = (
        {"severity": "high", "CWE": "CWE-79"},
        {"api_data": "test"},
    )
    mock_get_handler.return_value = mock_handler

    metadata, api_metadata = agent._extract_metadata(
        "https://test.com/123", "<html>test</html>", "https://test.com"
    )

    assert metadata["severity"] == "high"
    assert metadata["CWE"] == "CWE-79"
    assert api_metadata["api_data"] == "test"


@patch("messages.message_utils.log_message")
def test_write_import_bounty_message(mock_log, agent):
    """Test creating ImportBountyMessage."""
    mock_log.return_value = None

    bounty_dirs = ["dir1", "dir2"]
    bounty_links = ["link1", "link2"]

    message = agent._write_import_bounty_message(bounty_dirs, bounty_links, True)

    assert isinstance(message, ImportBountyMessage)
    assert message.bounty_dirs == bounty_dirs
    assert message.bounty_links == bounty_links
    assert message.success


@pytest.mark.asyncio
@patch(
    "agents.import_bounty_agent.import_bounty_agent.ImportBountyAgent._download_webpage"
)
@patch(
    "agents.import_bounty_agent.import_bounty_agent.ImportBountyAgent._extract_metadata"
)
@patch("agents.import_bounty_agent.import_bounty_agent.ImportBountyAgent._read_writeup")
@patch("messages.message_utils.log_message")
async def test_run(mock_log, mock_read_writeup, mock_extract_metadata, mock_download, agent):
    """Test full agent run."""
    test_dir = os.path.join("test_bounties", "report_123456")
    mock_download.return_value = test_dir
    mock_read_writeup.return_value = "<html>test content</html>"
    mock_extract_metadata.return_value = ({"test": "metadata"}, {"api": "data"})
    mock_log.return_value = None

    prev_message = WebscraperMessage(
        agent_id="test",
        message="test",
        website="https://hackerone.com/reports/",
        bounty_links=["https://hackerone.com/reports/123456"],
    )

    result = await agent.run([prev_message])

    assert isinstance(result, ImportBountyMessage)
    assert result.success
    assert result.bounty_dirs == [test_dir]
    assert result.bounty_links == ["https://hackerone.com/reports/123456"]


def test_read_writeup(agent):
    """Test reading writeup from file."""
    report_dir = os.path.join("test_bounties", "report_123456")
    os.makedirs(report_dir, exist_ok=True)
    html_content = "<html>test content</html>"

    with open(os.path.join(report_dir, "report_123456.html"), "w") as f:
        f.write(html_content)

    result = agent._read_writeup(report_dir)
    assert result == html_content

    empty_result = agent._read_writeup("non_existent_dir")
    assert empty_result == ""


@pytest.mark.asyncio
async def test_invalid_input_message(agent):
    """Test handling of invalid input messages."""
    with pytest.raises(ValueError):
        await agent.run([])  # Empty message list

    with pytest.raises(ValueError):
        await agent.run([Mock(), Mock()])  # Too many messages


def test_config_validation():
    """Test ImportBountyAgentConfig validation."""
    # Test valid config
    config = ImportBountyAgentConfig(bounty_dir="valid/path")
    assert config.bounty_dir == "valid/path"

    # Test config serialization
    config_dict = config.to_dict()
    assert config_dict["bounty_dir"] == "valid/path"

    # Test config deserialization
    new_config = ImportBountyAgentConfig.from_dict({"bounty_dir": "new/path"})
    assert new_config.bounty_dir == "new/path"


@patch("selenium.webdriver.Chrome")
@patch("agents.import_bounty_agent.import_bounty_agent.get_handler")
def test_download_webpage_error_handling(mock_get_handler, mock_chrome, agent):
    """Test error handling during webpage download."""
    mock_driver = MagicMock()
    mock_driver.get.side_effect = Exception("Network error")
    mock_chrome.return_value = mock_driver

    bounty_link = "https://hackerone.com/reports/123456"
    website = "https://hackerone.com/reports/"

    with pytest.raises(Exception) as cm:
        agent._download_webpage(bounty_link, website)

    assert "Network error" in str(cm.value)

    failed_links_file = os.path.join(agent.bounty_dir, "hackerone_failed_links.txt")
    assert os.path.exists(os.path.dirname(failed_links_file))

    # Verify the failed link was written
    with open(failed_links_file, "r") as f:
        failed_links = f.readlines()
    assert bounty_link + "\n" in failed_links


def test_write_api_metadata(agent):
    """Test writing API metadata to file."""
    report_dir = os.path.join("test_bounties", "report_test")
    os.makedirs(report_dir, exist_ok=True)

    api_metadata = {
        "severity": "critical",
        "bounty_amount": 500,
        "disclosed_at": "2024-03-20",
    }

    agent._write_api_metadata(report_dir, api_metadata)

    api_file = os.path.join(report_dir, "bounty_api_metadata.json")
    assert os.path.exists(api_file)

    with open(api_file, "r") as f:
        saved_metadata = json.load(f)
        assert saved_metadata == api_metadata


@patch("agents.import_bounty_agent.import_bounty_agent.get_handler")
def test_extract_metadata_no_handler(mock_get_handler, agent):
    """Test metadata extraction with no handler available."""
    mock_get_handler.return_value = None

    with pytest.raises(ValueError) as cm:
        agent._extract_metadata(
            "https://test.com/123", "<html>test</html>", "https://unsupported.com"
        )

    assert "No handler available" in str(cm.value)


@pytest.mark.asyncio
@patch(
    "agents.import_bounty_agent.import_bounty_agent.ImportBountyAgent._download_webpage"
)
@patch(
    "agents.import_bounty_agent.import_bounty_agent.ImportBountyAgent._extract_metadata"
)
@patch("agents.import_bounty_agent.import_bounty_agent.ImportBountyAgent._read_writeup")
@patch("messages.message_utils.log_message")
async def test_run_with_multiple_bounties(
    mock_log, mock_read_writeup, mock_extract_metadata, mock_download, agent
):
    """Test processing multiple bounty links."""
    mock_log.return_value = None
    mock_read_writeup.return_value = "<html>test content</html>"
    mock_extract_metadata.return_value = ({"test": "metadata"}, {"api": "data"})

    test_dirs = [
        os.path.join("test_bounties", "report_123"),
        os.path.join("test_bounties", "report_456"),
    ]
    mock_download.side_effect = test_dirs

    prev_message = WebscraperMessage(
        agent_id="test",
        message="test",
        website="https://hackerone.com/reports/",
        bounty_links=[
            "https://hackerone.com/reports/123",
            "https://hackerone.com/reports/456",
        ],
    )

    result = await agent.run([prev_message])

    assert len(result.bounty_dirs) == 2
    assert result.bounty_dirs == test_dirs
    assert mock_download.call_count == 2
    assert mock_extract_metadata.call_count == 2


@patch("selenium.webdriver.Chrome")
@patch("agents.import_bounty_agent.import_bounty_agent.get_handler")
def test_download_webpage_with_handler_error(mock_get_handler, mock_chrome, agent):
    """Test handling of handler errors during download."""
    mock_driver = MagicMock()
    mock_driver.page_source = "<html>Test content</html>"
    mock_chrome.return_value = mock_driver

    mock_handler = MagicMock()
    mock_handler.wait_for_page_load.side_effect = Exception("Handler error")
    mock_get_handler.return_value = mock_handler

    bounty_link = "https://hackerone.com/reports/123456"
    website = "https://hackerone.com/reports/"

    with pytest.raises(Exception) as cm:
        agent._download_webpage(bounty_link, website)

    assert "Handler error" in str(cm.value)
