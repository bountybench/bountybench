from browser_resource import BrowserResource
from messages.workflow_message import WorkflowMessage

# ✅ Ensure WorkflowMessage is initialized
WorkflowMessage.initialize("TestWorkflow")

# Define the configuration with the correct ChromeDriver path
config = {"driver_path": "chromedriver-mac-arm64/chromedriver"}  # Update path if needed

# Initialize the resource
resource = BrowserResource("test_browser_resource", config)

try:
    # Initialize WebDriver
    resource.init()

    # ✅ Test Case 1: Fill Form (Correct Form Selector)
    message1 = {
        "url": "https://demoqa.com/automation-practice-form",
        "message": "Command: Fill form\nForm Selector: #userForm\nName: John Doe\nEmail: johndoe@example.com\nPassword: 12345"
    }
    result1 = resource.run(message1)
    print("\n🚀 Test Case 1 (Fill Form) Result:\n", result1)

    # ✅ Test Case 2: Click Button (Ensure Button Selector Exists)
    message2 = {
        "url": "https://demoqa.com/automation-practice-form",
        "message": "Command: Click button\nButton Selector: button[id='submit']"
    }
    result2 = resource.run(message2)
    print("\n🚀 Test Case 2 (Click Button) Result:\n", result2)

    # ✅ Test Case 3: Navigate to a Page (Ensure `Navigate To:` is included)
    message3 = {
        "url": "https://example.com",
        "message": "Command: Navigate to https://example.com/profile"
    }
    result3 = resource.run(message3)
    print("\n🚀 Test Case 3 (Navigate) Result:\n", result3)

except Exception as e:
    print(f"\n❌ An error occurred: {e}")

finally:
    # Stop the WebDriver
    resource.stop()
