from tests.resources.browser_resource import BrowserResource
from messages.workflow_message import WorkflowMessage
from messages.action_messages.browser_message import BrowserMessage  # ✅ Use BrowserMessage
import traceback

# Initialize workflow logging
WorkflowMessage.initialize("TestWorkflow")

# Define configuration with ChromeDriver path
config = {"driver_path": "chromedriver-mac-arm64/chromedriver"}  # Update path if needed

# Initialize BrowserResource
resource = BrowserResource("test_browser_resource", config)
resource.init()

try:
    # ✅ Test Case 1: Fill Form
    message1 = BrowserMessage(  # ✅ Use BrowserMessage instead of Message
        resource_id="test_browser_resource",
        message="Command: fill form\nForm Selector: #userForm\nFirst Name: John\nLast Name: Doe\nUser Email: john.doe@example.com",
        additional_metadata={
            "url": "https://demoqa.com/automation-practice-form",
            "actions": ["fill_form"],
            "inputs": {
                "form_selector": "#userForm",
                "firstName": "John",
                "lastName": "Doe",
                "userEmail": "john.doe@example.com",
            },
        }
    )
    result1 = resource.run(message1)
    print("\n🚀 Test 1 (Fill Form) Result:\n", result1)

    # ✅ Test Case 2: Click Button
    message2 = BrowserMessage(  # ✅ Use BrowserMessage
        resource_id="test_browser_resource",
        message="Command: click button\nButton Selector: button[id='submit']",
        additional_metadata={
            "url": "https://demoqa.com/automation-practice-form",
            "actions": ["click_button"],
            "inputs": {"button_selector": "button[id='submit']"},
        }
    )
    result2 = resource.run(message2)
    print("\n🚀 Test 2 (Click Button) Result:\n", result2)

    # ✅ Test Case 3: Navigate to a Page
    message3 = BrowserMessage(  # ✅ Use BrowserMessage
        resource_id="test_browser_resource",
        message="Command: navigate\nNavigate To: https://example.com/profile",
        additional_metadata={
            "url": "https://example.com",
            "actions": ["navigate"],
            "inputs": {"navigate_to": "https://example.com/profile"},
        }
    )
    result3 = resource.run(message3)
    print("\n🚀 Test 3 (Navigate) Result:\n", result3)

except Exception as e:
    error_traceback = traceback.format_exc()
    print(error_traceback)
    print(f"\n❌ An error occurred: {e}")

finally:
    # Stop the WebDriver
    resource.stop()
