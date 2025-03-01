import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import os
import json

from agents.import_bounty_agent.import_bounty import ImportBountyAgent, ImportBountyAgentConfig
from messages.agent_messages.webscraper_agent_message import WebscraperMessage
from messages.agent_messages.import_bounty_agent_message import ImportBountyMessage

class TestImportBountyAgent(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_bounty_dir = "test_bounties"
        self.agent_config = ImportBountyAgentConfig(bounty_dir=self.test_bounty_dir)
        self.agent = ImportBountyAgent('import_bounty_agent', agent_config=self.agent_config)
        
        # Create test directories
        os.makedirs(self.test_bounty_dir, exist_ok=True)

    def tearDown(self):
        """Clean up test fixtures after each test method."""
        # Remove test directories and files
        if os.path.exists(self.test_bounty_dir):
            import shutil
            shutil.rmtree(self.test_bounty_dir)

    @patch("selenium.webdriver.Chrome")
    @patch("agents.import_bounty_agent.import_bounty.get_handler")
    def test_download_webpage(self, mock_get_handler, mock_chrome):
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
        
        report_dir = self.agent._download_webpage(bounty_link, website)
        
        # Verify handler methods were called
        mock_handler.wait_for_page_load.assert_called_once()
        mock_handler.scroll_to_load_content.assert_called_once()
        
        # Verify file was saved
        html_file = os.path.join(report_dir, "report_123456.html")
        self.assertTrue(os.path.exists(html_file))
        
        with open(html_file, 'r') as f:
            self.assertEqual(f.read(), "<html>Test content</html>")

    def test_write_bounty_metadata(self):
        """Test writing metadata to file."""
        report_dir = os.path.join(self.test_bounty_dir, "report_test")
        os.makedirs(report_dir, exist_ok=True)
        
        test_metadata = {
            "bounty_link": "https://test.com/123",
            "severity": "high",
            "CWE": "CWE-79"
        }
        
        self.agent._write_bounty_metadata(report_dir, test_metadata)
        
        metadata_file = os.path.join(report_dir, "bounty_metadata.json")
        self.assertTrue(os.path.exists(metadata_file))
        
        with open(metadata_file, 'r') as f:
            saved_metadata = json.load(f)
            self.assertEqual(saved_metadata, test_metadata)

    @patch("agents.import_bounty_agent.import_bounty.get_handler")
    def test_extract_metadata(self, mock_get_handler):
        """Test metadata extraction."""
        mock_handler = MagicMock()
        mock_handler.extract_metadata.return_value = (
            {"severity": "high", "CWE": "CWE-79"},
            {"api_data": "test"}
        )
        mock_get_handler.return_value = mock_handler
        
        metadata, api_metadata = self.agent._extract_metadata(
            "https://test.com/123",
            "<html>test</html>",
            "https://test.com"
        )
        
        self.assertEqual(metadata["severity"], "high")
        self.assertEqual(metadata["CWE"], "CWE-79")
        self.assertEqual(api_metadata["api_data"], "test")

    @patch("messages.message_utils.log_message")
    def test_write_import_bounty_message(self, mock_log):
        """Test creating ImportBountyMessage."""
        # Mock dependencies
        mock_log.return_value = None
        
        bounty_dirs = ["dir1", "dir2"]
        bounty_links = ["link1", "link2"]
        
        message = self.agent._write_import_bounty_message(bounty_dirs, bounty_links)
        
        self.assertIsInstance(message, ImportBountyMessage)
        self.assertEqual(message.bounty_dirs, bounty_dirs)
        self.assertEqual(message.bounty_links, bounty_links)
        self.assertTrue(message.success)

    @patch("agents.import_bounty_agent.import_bounty.ImportBountyAgent._download_webpage")
    @patch("agents.import_bounty_agent.import_bounty.ImportBountyAgent._extract_metadata")
    @patch("agents.import_bounty_agent.import_bounty.ImportBountyAgent._read_writeup")
    @patch("messages.message_utils.log_message")
    def test_run(self, mock_log, mock_read_writeup, mock_extract_metadata, mock_download):
        """Test full agent run."""
        # Mock dependencies
        test_dir = os.path.join(self.test_bounty_dir, "report_123456")
        mock_download.return_value = test_dir
        mock_read_writeup.return_value = "<html>test content</html>"
        mock_extract_metadata.return_value = ({"test": "metadata"}, {"api": "data"})
        mock_log.return_value = None
        
        # Create test message
        prev_message = WebscraperMessage(
            agent_id="test",
            message="test",
            website="https://hackerone.com/reports/",
            bounty_links=["https://hackerone.com/reports/123456"],
            success=True
        )
        
        result = self.agent.run([prev_message])
        
        # Verify the results
        self.assertIsInstance(result, ImportBountyMessage)
        self.assertTrue(result.success)
        self.assertEqual(result.bounty_dirs, [test_dir])
        self.assertEqual(result.bounty_links, ["https://hackerone.com/reports/123456"])
        
        # Verify all mocked methods were called correctly
        mock_download.assert_called_once_with(
            "https://hackerone.com/reports/123456",
            "https://hackerone.com/reports/"
        )
        mock_read_writeup.assert_called_once_with(test_dir)
        mock_extract_metadata.assert_called_once_with(
            "https://hackerone.com/reports/123456",
            "<html>test content</html>",
            "https://hackerone.com/reports/"
        )

    def test_read_writeup(self):
        """Test reading writeup from file."""
        # Create test report directory and file
        report_dir = os.path.join(self.test_bounty_dir, "report_123456")
        os.makedirs(report_dir, exist_ok=True)
        html_content = "<html>test content</html>"
        
        with open(os.path.join(report_dir, "report_123456.html"), "w") as f:
            f.write(html_content)
            
        # Test reading existing file
        result = self.agent._read_writeup(report_dir)
        self.assertEqual(result, html_content)
        
        # Test reading non-existent file
        empty_result = self.agent._read_writeup("non_existent_dir")
        self.assertEqual(empty_result, "")

    def test_invalid_input_message(self):
        """Test handling of invalid input messages."""
        with self.assertRaises(ValueError):
            self.agent.run([])  # Empty message list
            
        with self.assertRaises(ValueError):
            self.agent.run([Mock(), Mock()])  # Too many messages

    def test_config_validation(self):
        """Test ImportBountyAgentConfig validation."""
        # Test valid config
        config = ImportBountyAgentConfig(bounty_dir="valid/path")
        self.assertEqual(config.bounty_dir, "valid/path")
        
        # Test config serialization
        config_dict = config.to_dict()
        self.assertEqual(config_dict["bounties_dir"], "valid/path")
        
        # Test config deserialization
        new_config = ImportBountyAgentConfig.from_dict({"bounty_dir": "new/path"})
        self.assertEqual(new_config.bounty_dir, "new/path")

    @patch("selenium.webdriver.Chrome")
    @patch("agents.import_bounty_agent.import_bounty.get_handler")
    def test_download_webpage_error_handling(self, mock_get_handler, mock_chrome):
        """Test error handling during webpage download."""
        # Mock Chrome driver to raise exception
        mock_driver = MagicMock()
        mock_driver.get.side_effect = Exception("Network error")
        mock_chrome.return_value = mock_driver
        
        bounty_link = "https://hackerone.com/reports/123456"
        website = "https://hackerone.com/reports/"
        
        with self.assertRaises(Exception) as cm:
            self.agent._download_webpage(bounty_link, website)
        
        self.assertIn("Network error", str(cm.exception))
        
        # Verify failed link was saved
        failed_links_file = os.path.join("reports", "hackerone_reports", "failed_links.txt")
        self.assertTrue(os.path.exists(os.path.dirname(failed_links_file)))

    def test_write_api_metadata(self):
        """Test writing API metadata to file."""
        report_dir = os.path.join(self.test_bounty_dir, "report_test")
        os.makedirs(report_dir, exist_ok=True)
        
        api_metadata = {
            "severity": "critical",
            "bounty_amount": 500,
            "disclosed_at": "2024-03-20"
        }
        
        self.agent._write_api_metadata(report_dir, api_metadata)
        
        # Verify file was created with correct content
        api_file = os.path.join(report_dir, "bounty_api_metadata.json")
        self.assertTrue(os.path.exists(api_file))
        
        with open(api_file, 'r') as f:
            saved_metadata = json.load(f)
            self.assertEqual(saved_metadata, api_metadata)

    @patch("agents.import_bounty_agent.import_bounty.get_handler")
    def test_extract_metadata_no_handler(self, mock_get_handler):
        """Test metadata extraction with no handler available."""
        mock_get_handler.return_value = None
        
        with self.assertRaises(ValueError) as cm:
            self.agent._extract_metadata(
                "https://test.com/123",
                "<html>test</html>",
                "https://unsupported.com"
            )
        
        self.assertIn("No handler available", str(cm.exception))

    @patch("agents.import_bounty_agent.import_bounty.ImportBountyAgent._download_webpage")
    @patch("agents.import_bounty_agent.import_bounty.ImportBountyAgent._extract_metadata")
    @patch("agents.import_bounty_agent.import_bounty.ImportBountyAgent._read_writeup")
    @patch("messages.message_utils.log_message")
    def test_run_with_multiple_bounties(self, mock_log, mock_read_writeup, mock_extract_metadata, mock_download):
        """Test processing multiple bounty links."""
        # Mock dependencies
        mock_log.return_value = None
        mock_read_writeup.return_value = "<html>test content</html>"
        mock_extract_metadata.return_value = ({"test": "metadata"}, {"api": "data"})
        
        test_dirs = [
            os.path.join(self.test_bounty_dir, "report_123"),
            os.path.join(self.test_bounty_dir, "report_456")
        ]
        mock_download.side_effect = test_dirs
        
        # Create test message with multiple bounty links
        prev_message = WebscraperMessage(
            agent_id="test",
            message="test",
            website="https://hackerone.com/reports/",
            bounty_links=[
                "https://hackerone.com/reports/123",
                "https://hackerone.com/reports/456"
            ],
            success=True
        )
        
        result = self.agent.run([prev_message])
        
        # Verify results
        self.assertEqual(len(result.bounty_dirs), 2)
        self.assertEqual(result.bounty_dirs, test_dirs)
        self.assertEqual(mock_download.call_count, 2)
        self.assertEqual(mock_extract_metadata.call_count, 2)

    @patch('builtins.open')
    @patch('os.makedirs')
    def test_write_bounty_metadata_error(self, mock_makedirs, mock_open):
        """Test error handling when writing metadata fails."""
        report_dir = os.path.join(self.test_bounty_dir, "report_test")
        
        # Mock open to raise an error
        mock_open.side_effect = OSError("Failed to write file")
        # Mock makedirs to do nothing
        mock_makedirs.return_value = None
        
        with self.assertRaises(OSError) as cm:
            self.agent._write_bounty_metadata(report_dir, {"test": "data"})
        
        self.assertEqual(str(cm.exception), "Failed to write file")
            
        # Verify makedirs was called
        mock_makedirs.assert_called_once_with(os.path.dirname(os.path.join(report_dir, "bounty_metadata.json")), exist_ok=True)
        # Verify open was called
        mock_open.assert_called_once()

    @patch("selenium.webdriver.Chrome")
    @patch("agents.import_bounty_agent.import_bounty.get_handler")
    def test_download_webpage_with_handler_error(self, mock_get_handler, mock_chrome):
        """Test handling of handler errors during download."""
        # Mock Chrome driver
        mock_driver = MagicMock()
        mock_driver.page_source = "<html>Test content</html>"
        mock_chrome.return_value = mock_driver
        
        # Mock handler to raise exception
        mock_handler = MagicMock()
        mock_handler.wait_for_page_load.side_effect = Exception("Handler error")
        mock_get_handler.return_value = mock_handler
        
        bounty_link = "https://hackerone.com/reports/123456"
        website = "https://hackerone.com/reports/"
        
        with self.assertRaises(Exception) as cm:
            self.agent._download_webpage(bounty_link, website)
        
        self.assertIn("Handler error", str(cm.exception))

if __name__ == '__main__':
    unittest.main() 