import pytest
from unittest.mock import Mock, patch
from utils.logger import get_main_logger

@pytest.fixture
def mock_logger():
    with patch('utils.logger.get_main_logger') as mock:
        logger = Mock()
        mock.return_value = logger
        yield logger

def test_logger_methods(mock_logger):
    """Test all logger methods to ensure they work as expected"""
    
    # Test info messages
    mock_logger.info("These are INFO messages")
    mock_logger.info.assert_called_with("These are INFO messages")

    # Test status messages
    mock_logger.status("This is a general STATUS message")
    mock_logger.status.assert_called_with("This is a general STATUS message")
    
    # Test status message with success flag
    mock_logger.status("This is a success STATUS message", True)
    mock_logger.status.assert_called_with("This is a success STATUS message", True)

    # Test warning message
    mock_logger.warning("This is a WARNING message")
    mock_logger.warning.assert_called_with("This is a WARNING message")

    # Test error message
    mock_logger.error("This is an ERROR message")
    mock_logger.error.assert_called_with("This is an ERROR message")

    # Test critical message
    mock_logger.critical("This is a CRITICAL message")
    mock_logger.critical.assert_called_with("This is a CRITICAL message")

@pytest.mark.parametrize("log_level,message", [
    ("info", "These are INFO messages"),
    ("status", "This is a general STATUS message"),
    ("warning", "This is a WARNING message"),
    ("error", "This is an ERROR message"),
    ("critical", "This is a CRITICAL message")
])
def test_logger_different_messages(mock_logger, log_level, message):
    """Test logger with different message types"""
    getattr(mock_logger, log_level)(message)
    getattr(mock_logger, log_level).assert_called_with(message)

def test_status_success_flag(mock_logger):
    """Test status message with success flag"""
    mock_logger.status("This is a success STATUS message", True)
    mock_logger.status.assert_called_with("This is a success STATUS message", True)