import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio

from agents.webscraper_agent.webscraper_agent import WebscraperAgent, WebscraperAgentConfig
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.import_bounty_agent_message import ImportBountyMessage
from messages.agent_messages.webscraper_agent_message import WebscraperMessage

@pytest.fixture
def agents():
    """Set up test fixtures before each test method."""
    huntr_config = WebscraperAgentConfig(website="https://huntr.com/bounties")
    hackerone_config = WebscraperAgentConfig(website="https://hackerone.com/reports/")
    
    huntr_agent = WebscraperAgent('webscraper_agent', agent_config=huntr_config)
    hackerone_agent = WebscraperAgent('webscraper_agent', agent_config=hackerone_config)
    return huntr_agent, hackerone_agent

def test_agent_initialization(agents):
    """Test agent initialization with different configs."""
    huntr_agent, hackerone_agent = agents
    assert huntr_agent.website == "https://huntr.com/bounties"
    assert hackerone_agent.website == "https://hackerone.com/reports/"
    
    # Test invalid website
    with pytest.raises(ValueError):
        invalid_config = WebscraperAgentConfig(website="https://invalid.com")
        WebscraperAgent('webscraper_agent', agent_config=invalid_config)

@pytest.mark.asyncio
@patch("messages.message_utils.log_message")
async def test_huntr_agent_with_no_previous_links(mock_log, agents):
    """Test Huntr agent with no previous bounty links."""
    huntr_agent, _ = agents
    mock_log.return_value = None
    
    # Mock the handler methods
    huntr_agent.handler.get_known_urls = MagicMock(return_value=set())
    huntr_agent.handler.get_latest_report_urls = MagicMock(
        return_value=[
            "https://huntr.com/bounties/new-bounty-1",
            "https://huntr.com/bounties/new-bounty-2"
        ]
    )
    huntr_agent.handler.save_urls_to_file = MagicMock()
    
    prev_message = ImportBountyMessage(
        agent_id="test",
        message="test",
        bounty_links=[],
        bounty_dirs=[],
        success=True,
        prev=None
    )
    
    result = await huntr_agent.run([prev_message])
    
    assert isinstance(result, WebscraperMessage)
    assert len(result.bounty_links) == 2
    assert result.website == "https://huntr.com/bounties"

@pytest.mark.asyncio
@patch("messages.message_utils.log_message")
async def test_hackerone_agent_with_previous_links(mock_log, agents):
    """Test HackerOne agent with previous bounty links."""
    _, hackerone_agent = agents
    mock_log.return_value = None
    
    known_urls = {"https://hackerone.com/reports/old-report"}
    latest_urls = [
        "https://hackerone.com/reports/new-report-1",
        "https://hackerone.com/reports/new-report-2",
        "https://hackerone.com/reports/old-report"
    ]
    
    hackerone_agent.handler.get_known_urls = MagicMock(return_value=known_urls)
    hackerone_agent.handler.get_latest_report_urls = MagicMock(return_value=latest_urls)
    hackerone_agent.handler.save_urls_to_file = MagicMock()
    
    prev_message = ImportBountyMessage(
        agent_id="test",
        message="test",
        bounty_links=["https://hackerone.com/reports/old-report"],
        bounty_dirs=[],
        success=True,
        prev=None
    )
    
    result = await hackerone_agent.run([prev_message])
    
    assert len(result.bounty_links) == 2
    assert result.bounty_links[0] == "https://hackerone.com/reports/new-report-1"

@pytest.mark.asyncio
@patch("messages.message_utils.log_message")
async def test_error_handling(mock_log, agents):
    """Test error handling during URL fetching."""
    huntr_agent, _ = agents
    mock_log.return_value = None
    
    # Mock handler to raise an exception
    huntr_agent.handler.get_latest_report_urls = MagicMock(
        side_effect=[Exception("Network error"), ["https://huntr.com/bounties/new-bounty"]]
    )
    huntr_agent.handler.save_urls_to_file = MagicMock()
    
    # Mock sleep to avoid waiting
    with patch('asyncio.sleep', return_value=None):
        result = await huntr_agent.run([
            ImportBountyMessage(
                agent_id="test",
                message="test",
                bounty_links=[],
                bounty_dirs=[],
                success=True,
                prev=None
            )
        ])
    
    assert len(result.bounty_links) == 1

@patch("messages.message_utils.log_message")
def test_webscraper_message_serialization(mock_log):
    """Test WebscraperMessage serialization."""
    mock_log.return_value = None

    message = WebscraperMessage(
        agent_id="test",
        message="Test message",
        website="https://huntr.com/bounties",
        bounty_links=["https://huntr.com/bounties/test-1"],
    )
    
    message_dict = message.to_log_dict()
    
    assert message_dict["agent_id"] == "test"
    assert message_dict["message"] == "Test message"
    assert message_dict["website"] == "https://huntr.com/bounties"
    assert message_dict["bounty_links"] == ["https://huntr.com/bounties/test-1"]

@pytest.mark.asyncio
@patch("messages.message_utils.log_message")
async def test_no_new_urls_found(mock_log, agents):
    """Test behavior when no new URLs are found."""
    huntr_agent, _ = agents
    mock_log.return_value = None
    
    known_urls = {
        "https://huntr.com/bounties/existing-1",
        "https://huntr.com/bounties/existing-2"
    }
    latest_urls = [
        "https://huntr.com/bounties/existing-1",
        "https://huntr.com/bounties/existing-2"
    ]
    
    huntr_agent.handler.get_known_urls = MagicMock(return_value=known_urls)
    huntr_agent.handler.get_latest_report_urls = MagicMock(return_value=latest_urls)
    huntr_agent.handler.save_urls_to_file = MagicMock()
    
    # Mock sleep to avoid waiting
    with patch('asyncio.sleep', side_effect=[None, Exception("Test timeout")]):
        with pytest.raises(Exception):
            await huntr_agent.run([
                ImportBountyMessage(
                    agent_id="test",
                    message="test",
                    bounty_links=[],
                    bounty_dirs=[],
                    success=True,
                    prev=None
                )
            ])
    
    # Verify save_urls_to_file was not called
    huntr_agent.handler.save_urls_to_file.assert_not_called()

@pytest.mark.asyncio
@patch("messages.message_utils.log_message")
async def test_multiple_retries(mock_log, agents):
    """Test multiple retry attempts on failure."""
    huntr_agent, _ = agents
    mock_log.return_value = None
    
    huntr_agent.handler.get_latest_report_urls = MagicMock(
        side_effect=[
            Exception("First error"),
            Exception("Second error"),
            ["https://huntr.com/bounties/success"]
        ]
    )
    huntr_agent.handler.get_known_urls = MagicMock(return_value=set())
    huntr_agent.handler.save_urls_to_file = MagicMock()
    
    # Mock sleep to avoid waiting
    with patch('asyncio.sleep', return_value=None):
        result = await huntr_agent.run([
            ImportBountyMessage(
                agent_id="test",
                message="test",
                bounty_links=[],
                bounty_dirs=[],
                success=True,
                prev=None
            )
        ])
    
    assert len(result.bounty_links) == 1
    assert result.bounty_links[0] == "https://huntr.com/bounties/success"
    
    # Verify get_latest_report_urls was called 3 times
    assert huntr_agent.handler.get_latest_report_urls.call_count == 3

@pytest.mark.asyncio
@patch("messages.message_utils.log_message")
async def test_duplicate_url_handling(mock_log, agents):
    """Test handling of duplicate URLs in latest reports."""
    huntr_agent, _ = agents
    mock_log.return_value = None
    
    latest_urls = [
        "https://huntr.com/bounties/new-1",
        "https://huntr.com/bounties/new-1",  # Duplicate
        "https://huntr.com/bounties/new-2",
        "https://huntr.com/bounties/new-2",  # Duplicate
        "https://huntr.com/bounties/new-3"
    ]
    
    huntr_agent.handler.get_known_urls = MagicMock(return_value=set())
    huntr_agent.handler.get_latest_report_urls = MagicMock(return_value=latest_urls)
    huntr_agent.handler.save_urls_to_file = MagicMock()
    
    result = await huntr_agent.run([
        ImportBountyMessage(
            agent_id="test",
            message="test",
            bounty_links=[],
            bounty_dirs=[],
            success=True,
            prev=None
        )
    ])
    
    # Verify duplicates are removed
    assert len(result.bounty_links) == 3
    assert len(set(result.bounty_links)) == 3  # Verify all URLs are unique
    assert result.bounty_links == [
        "https://huntr.com/bounties/new-1",
        "https://huntr.com/bounties/new-2",
        "https://huntr.com/bounties/new-3"
    ]

def test_invalid_message_chain():
    """Test handling of invalid message chain."""
    invalid_inputs = [
        (None, "bounty_links cannot be None"),
        ("not_a_list", "bounty_links must be a list")
    ]

    for invalid_input, expected_error in invalid_inputs:
        with pytest.raises(ValueError) as cm:
            WebscraperMessage(
                agent_id="test",
                message="Test message",
                website="https://huntr.com/bounties",
                bounty_links=invalid_input,
            )
        assert str(cm.value) == expected_error

def test_webscraper_config_validation():
    """Test WebscraperAgentConfig validation and serialization."""
    # Test valid configs
    config1 = WebscraperAgentConfig(website="https://huntr.com/bounties")
    assert config1.website == "https://huntr.com/bounties"
    
    config2 = WebscraperAgentConfig(website="https://hackerone.com/reports/")
    assert config2.website == "https://hackerone.com/reports/"
    
    # Test invalid configs
    with pytest.raises(ValueError):
        WebscraperAgentConfig(website="https://invalid.com")
