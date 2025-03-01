import unittest
from unittest.mock import Mock, patch, MagicMock
import asyncio

from agents.webscraper_agent.webscraper_agent import WebscraperAgent, WebscraperAgentConfig
from messages.agent_messages.agent_message import AgentMessage
from messages.agent_messages.import_bounty_agent_message import ImportBountyMessage
from messages.agent_messages.webscraper_agent_message import WebscraperMessage

class TestWebscraperAgent(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.huntr_config = WebscraperAgentConfig(website="https://huntr.com/bounties")
        self.hackerone_config = WebscraperAgentConfig(website="https://hackerone.com/reports/")
        
        self.huntr_agent = WebscraperAgent('webscraper_agent', agent_config=self.huntr_config)
        self.hackerone_agent = WebscraperAgent('webscraper_agent', agent_config=self.hackerone_config)

    def test_agent_initialization(self):
        """Test agent initialization with different configs."""
        self.assertEqual(self.huntr_agent.website, "https://huntr.com/bounties")
        self.assertEqual(self.hackerone_agent.website, "https://hackerone.com/reports/")
        
        # Test invalid website
        with self.assertRaises(ValueError):
            invalid_config = WebscraperAgentConfig(website="https://invalid.com")
            WebscraperAgent('webscraper_agent', agent_config=invalid_config)

    @patch("messages.message_utils.log_message")
    async def test_huntr_agent_with_no_previous_links(self, mock_log):
        """Test Huntr agent with no previous bounty links."""
        mock_log.return_value = None
        
        # Mock the handler methods
        self.huntr_agent.handler.get_known_urls = MagicMock(return_value=set())
        self.huntr_agent.handler.get_latest_report_urls = MagicMock(
            return_value=[
                "https://huntr.com/bounties/new-bounty-1",
                "https://huntr.com/bounties/new-bounty-2"
            ]
        )
        self.huntr_agent.handler.save_urls_to_file = MagicMock()
        
        prev_message = ImportBountyMessage(
            agent_id="test",
            message="test",
            bounty_links=[],
            bounty_dirs=[],
            success=True,
            prev=None
        )
        
        result = await self.huntr_agent.run([prev_message])
        
        self.assertIsInstance(result, WebscraperMessage)
        self.assertEqual(len(result.bounty_links), 2)
        self.assertEqual(result.website, "https://huntr.com/bounties")
        self.assertTrue(result.success)

    @patch("messages.message_utils.log_message")
    async def test_hackerone_agent_with_previous_links(self, mock_log):
        """Test HackerOne agent with previous bounty links."""
        mock_log.return_value = None
        
        known_urls = {"https://hackerone.com/reports/old-report"}
        latest_urls = [
            "https://hackerone.com/reports/new-report-1",
            "https://hackerone.com/reports/new-report-2",
            "https://hackerone.com/reports/old-report"
        ]
        
        self.hackerone_agent.handler.get_known_urls = MagicMock(return_value=known_urls)
        self.hackerone_agent.handler.get_latest_report_urls = MagicMock(return_value=latest_urls)
        self.hackerone_agent.handler.save_urls_to_file = MagicMock()
        
        prev_message = ImportBountyMessage(
            agent_id="test",
            message="test",
            bounty_links=["https://hackerone.com/reports/old-report"],
            bounty_dirs=[],
            success=True,
            prev=None
        )
        
        result = await self.hackerone_agent.run([prev_message])
        
        self.assertEqual(len(result.bounty_links), 2)
        self.assertEqual(result.bounty_links[0], "https://hackerone.com/reports/new-report-1")

    @patch("messages.message_utils.log_message")
    async def test_error_handling(self, mock_log):
        """Test error handling during URL fetching."""
        mock_log.return_value = None
        
        # Mock handler to raise an exception
        self.huntr_agent.handler.get_latest_report_urls = MagicMock(
            side_effect=[Exception("Network error"), ["https://huntr.com/bounties/new-bounty"]]
        )
        self.huntr_agent.handler.save_urls_to_file = MagicMock()
        
        # Mock sleep to avoid waiting
        with patch('asyncio.sleep', return_value=None):
            result = await self.huntr_agent.run([
                ImportBountyMessage(
                    agent_id="test",
                    message="test",
                    bounty_links=[],
                    bounty_dirs=[],
                    success=True,
                    prev=None
                )
            ])
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.bounty_links), 1)

    @patch("messages.message_utils.log_message")
    def test_webscraper_message_serialization(self, mock_log):
        """Test WebscraperMessage serialization."""
        mock_log.return_value = None

        message = WebscraperMessage(
            agent_id="test",
            message="Test message",
            website="https://huntr.com/bounties",
            bounty_links=["https://huntr.com/bounties/test-1"],
            success=True
        )
        
        message_dict = message.to_log_dict()
        
        self.assertEqual(message_dict["agent_id"], "test")
        self.assertEqual(message_dict["message"], "Test message")
        self.assertEqual(message_dict["website"], "https://huntr.com/bounties")
        self.assertEqual(message_dict["bounty_links"], ["https://huntr.com/bounties/test-1"])
        self.assertTrue(message_dict["success"])

    @patch("messages.message_utils.log_message")
    async def test_no_new_urls_found(self, mock_log):
        """Test behavior when no new URLs are found."""
        mock_log.return_value = None
        
        known_urls = {
            "https://huntr.com/bounties/existing-1",
            "https://huntr.com/bounties/existing-2"
        }
        latest_urls = [
            "https://huntr.com/bounties/existing-1",
            "https://huntr.com/bounties/existing-2"
        ]
        
        self.huntr_agent.handler.get_known_urls = MagicMock(return_value=known_urls)
        self.huntr_agent.handler.get_latest_report_urls = MagicMock(return_value=latest_urls)
        self.huntr_agent.handler.save_urls_to_file = MagicMock()
        
        # Mock sleep to avoid waiting
        with patch('asyncio.sleep', side_effect=[None, Exception("Test timeout")]):
            with self.assertRaises(Exception):
                await self.huntr_agent.run([
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
        self.huntr_agent.handler.save_urls_to_file.assert_not_called()

    @patch("messages.message_utils.log_message")
    async def test_multiple_retries(self, mock_log):
        """Test multiple retry attempts on failure."""
        mock_log.return_value = None
        
        self.huntr_agent.handler.get_latest_report_urls = MagicMock(
            side_effect=[
                Exception("First error"),
                Exception("Second error"),
                ["https://huntr.com/bounties/success"]
            ]
        )
        self.huntr_agent.handler.get_known_urls = MagicMock(return_value=set())
        self.huntr_agent.handler.save_urls_to_file = MagicMock()
        
        # Mock sleep to avoid waiting
        with patch('asyncio.sleep', return_value=None):
            result = await self.huntr_agent.run([
                ImportBountyMessage(
                    agent_id="test",
                    message="test",
                    bounty_links=[],
                    bounty_dirs=[],
                    success=True,
                    prev=None
                )
            ])
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.bounty_links), 1)
        self.assertEqual(result.bounty_links[0], "https://huntr.com/bounties/success")
        
        # Verify get_latest_report_urls was called 3 times
        self.assertEqual(self.huntr_agent.handler.get_latest_report_urls.call_count, 3)

    @patch("messages.message_utils.log_message")
    async def test_duplicate_url_handling(self, mock_log):
        """Test handling of duplicate URLs in latest reports."""
        mock_log.return_value = None
        
        latest_urls = [
            "https://huntr.com/bounties/new-1",
            "https://huntr.com/bounties/new-1",  # Duplicate
            "https://huntr.com/bounties/new-2",
            "https://huntr.com/bounties/new-2",  # Duplicate
            "https://huntr.com/bounties/new-3"
        ]
        
        self.huntr_agent.handler.get_known_urls = MagicMock(return_value=set())
        self.huntr_agent.handler.get_latest_report_urls = MagicMock(return_value=latest_urls)
        self.huntr_agent.handler.save_urls_to_file = MagicMock()
        
        result = await self.huntr_agent.run([
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
        self.assertEqual(len(result.bounty_links), 3)
        self.assertEqual(len(set(result.bounty_links)), 3)  # Verify all URLs are unique
        self.assertEqual(result.bounty_links, [
            "https://huntr.com/bounties/new-1",
            "https://huntr.com/bounties/new-2",
            "https://huntr.com/bounties/new-3"
        ])

    @patch("messages.message_utils.log_message")
    def test_invalid_message_chain(self, mock_log):
        """Test handling of invalid message chain."""
        mock_log.return_value = None

        invalid_inputs = [
            (None, "bounty_links cannot be None"),
            ("not_a_list", "bounty_links must be a list")
        ]

        for invalid_input, expected_error in invalid_inputs:
            with self.assertRaises(ValueError) as cm:
                WebscraperMessage(
                    agent_id="test",
                    message="Test message",
                    website="https://huntr.com/bounties",
                    bounty_links=invalid_input,
                    success=True
                )
            self.assertEqual(str(cm.exception), expected_error)

    def test_webscraper_config_validation(self):
        """Test WebscraperAgentConfig validation and serialization."""
        # Test valid configs
        config1 = WebscraperAgentConfig(website="https://huntr.com/bounties")
        self.assertEqual(config1.website, "https://huntr.com/bounties")
        
        config2 = WebscraperAgentConfig(website="https://hackerone.com/reports/")
        self.assertEqual(config2.website, "https://hackerone.com/reports/")
        
        # Test invalid configs - combine into one block to avoid unreachable code
        invalid_configs = [
            "",  # Empty website
            "https://invalid.com",  # Unsupported website
        ]
        for invalid_config in invalid_configs:
            with self.assertRaises(ValueError):
                WebscraperAgentConfig(website=invalid_config)
        
        # Test invalid dict
        with self.assertRaises(ValueError):
            WebscraperAgentConfig.from_dict({})  # Missing website key

if __name__ == '__main__':
    unittest.main()
