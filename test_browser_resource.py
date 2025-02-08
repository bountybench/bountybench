import sys
import os

# ✅ Ensure Python can find `messages`
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from browser_resource import BrowserResource
from messages.action_messages.command_message import CommandMessage
from messages.workflow_message import WorkflowMessage  # ✅ Import WorkflowMessage

# ✅ Initialize WorkflowMessage (Required to prevent errors)
WorkflowMessage.initialize("TestWorkflow")

# ✅ Setup WebDriver
config = {"driver_path": "chromedriver-mac-arm64/chromedriver"}
resource = BrowserResource("test_browser_resource", config)

try:
    resource.init()

    # ✅ Test 1: Fill Form (Ensure "Command:" is formatted correctly)
    message1 = {
        "url": "https://demoqa.com/automation-practice-form",
        "message": "Command: fill form\nForm Selector: #userForm\nFirst Name: John\nLast Name: Doe\nUser Email: john.doe@example.com",
        "actions": ["fill_form"],
        "inputs": {
            "form_selector": "#userForm",  # ✅ Fix: Provide selector
            "firstName": "John",
            "lastName": "Doe",
            "userEmail": "john.doe@example.com"
        }
    }
    print("\n🔍 Debugging message1:", message1)  # ✅ Debugging

    command_message = CommandMessage(resource.resource_id, message1["message"])
    print(f"\n✅ Extracted Command: {command_message.command}")  # ✅ Debugging

    result1 = resource.run(message1)
    print("\n🚀 Test 1 (Fill Form) Result:\n", result1)

    # ✅ Test 2: Click Button (Ensure Button Selector is Provided)
    message2 = {
        "url": "https://demoqa.com/automation-practice-form",
        "message": "Command: click button\nButton Selector: button[id='submit']",
        "actions": ["click_button"],
        "inputs": {
            "button_selector": "button[id='submit']"
        }
    }
    print("\n🔍 Debugging message2:", message2)  # ✅ Debugging

    result2 = resource.run(message2)
    print("\n🚀 Test 2 (Click Button) Result:\n", result2)

    # ✅ Test 3: Navigate to a Page (Ensure `"Navigate To:"` is included)
    message3 = {
        "url": "https://example.com",
        "message": "Command: navigate\nNavigate To: https://example.com/profile",
        "actions": ["navigate"],
        "inputs": {
            "navigate_to": "https://example.com/profile"  # ✅ Fix: Provide explicit URL
        }
    }
    print("\n🔍 Debugging message3:", message3)  # ✅ Debugging

    result3 = resource.run(message3)
    print("\n🚀 Test 3 (Navigate) Result:\n", result3)

except Exception as e:
    print(f"\n❌ An error occurred: {e}")

finally:
    resource.stop()
