import "@testing-library/jest-dom/extend-expect";
import React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";
import AgentMessage from "./AgentMessage/AgentMessage";
import { ThemeProvider } from "@mui/material/styles";
import { darkTheme } from "../../../theme";

// Mock setTimeout to execute immediately
jest.useFakeTimers();

// Add mock for scrollIntoView
beforeAll(() => {
  // Create a mock implementation for scrollIntoView
  window.HTMLElement.prototype.scrollIntoView = jest.fn();
});

// Clean up after tests
afterAll(() => {
  // Remove the mock
  delete window.HTMLElement.prototype.scrollIntoView;
});

describe("AgentMessage navigation functionality", () => {
  // Mock data setup
  const parentMessage = {
    current_id: "parent_id",
    current_children: [
      { current_id: "child1" },
      { current_id: "child2" },
      { current_id: "child3" }
    ]
  };

  const message = {
    agent_id: "executor_agent",
    message: "test message",
    current_id: "child2",
    current_children: []  // Empty children array allows editing
  };

  const mockOnCellSelect = jest.fn();
  const mockOnEditingChange = jest.fn();
  const mockOnUpdateMessageInput = jest.fn();

  beforeEach(() => {
    mockOnCellSelect.mockClear();
    mockOnEditingChange.mockClear();
    mockOnUpdateMessageInput.mockClear();
    jest.clearAllTimers();
    
    // Clear the scrollIntoView mock for each test
    if (window.HTMLElement.prototype.scrollIntoView.mockClear) {
      window.HTMLElement.prototype.scrollIntoView.mockClear();
    }
  });

  test("handleMoveUp navigates to previous sibling", () => {
    render(
      <ThemeProvider theme={darkTheme}>
        <AgentMessage 
          index={1} 
          message={message} 
          onCellSelect={mockOnCellSelect} 
          parentMessage={parentMessage}
          selectedCellId={message.current_id}
        />
      </ThemeProvider>
    );

    // Trigger up navigation with keyboard
    fireEvent.keyDown(document, { key: "ArrowUp" });
    act(() => {
      jest.runAllTimers();
    });

    // Should select the previous child
    expect(mockOnCellSelect).toHaveBeenCalledWith("child1");
  });

  // [Rest of the test code remains unchanged]
  test("handleMoveDown navigates to next sibling", () => {
    render(
      <ThemeProvider theme={darkTheme}>
        <AgentMessage 
          index={1} 
          message={message} 
          onCellSelect={mockOnCellSelect} 
          parentMessage={parentMessage}
          selectedCellId={message.current_id}
        />
      </ThemeProvider>
    );

    // Trigger down navigation with keyboard
    fireEvent.keyDown(document, { key: "ArrowDown" });
    act(() => {
      jest.runAllTimers();
    });

    // Should select the next child
    expect(mockOnCellSelect).toHaveBeenCalledWith("child3");
  });

  test("handleMoveLeft navigates to parent", () => {
    render(
      <ThemeProvider theme={darkTheme}>
        <AgentMessage 
          index={1} 
          message={message} 
          onCellSelect={mockOnCellSelect} 
          parentMessage={parentMessage}
          selectedCellId={message.current_id}
        />
      </ThemeProvider>
    );

    // Trigger left navigation with keyboard
    fireEvent.keyDown(document, { key: "ArrowLeft" });
    act(() => {
      jest.runAllTimers();
    });

    // Should select the parent
    expect(mockOnCellSelect).toHaveBeenCalledWith("parent_id");
  });

  test("handleMoveRight navigates to first child", () => {
    // For this test, we need to use a message with children
    const messageWithChildren = {
      ...message,
      current_children: [
        { current_id: "grandchild1" },
        { current_id: "grandchild2" }
      ]
    };

    render(
      <ThemeProvider theme={darkTheme}>
        <AgentMessage 
          index={1} 
          message={messageWithChildren} 
          onCellSelect={mockOnCellSelect} 
          parentMessage={parentMessage}
          selectedCellId={messageWithChildren.current_id}
        />
      </ThemeProvider>
    );

    // Trigger right navigation with keyboard
    fireEvent.keyDown(document, { key: "ArrowRight" });
    act(() => {
      jest.runAllTimers();
    });

    // Should select the first child
    expect(mockOnCellSelect).toHaveBeenCalledWith("grandchild1");
  });

  test("alternative WASD navigation works", () => {
    render(
      <ThemeProvider theme={darkTheme}>
        <AgentMessage 
          index={1} 
          message={message} 
          onCellSelect={mockOnCellSelect} 
          parentMessage={parentMessage}
          selectedCellId={message.current_id}
        />
      </ThemeProvider>
    );

    // Test WASD keys
    fireEvent.keyDown(document, { key: "w" }); // up
    act(() => { jest.runAllTimers(); });
    expect(mockOnCellSelect).toHaveBeenNthCalledWith(1, "child1");

    fireEvent.keyDown(document, { key: "s" }); // down
    act(() => { jest.runAllTimers(); });
    expect(mockOnCellSelect).toHaveBeenNthCalledWith(2, "child3");

    fireEvent.keyDown(document, { key: "a" }); // left
    act(() => { jest.runAllTimers(); });
    expect(mockOnCellSelect).toHaveBeenNthCalledWith(3, "parent_id");
  });

  test("navigation is correctly blocked during editing mode", () => {
    const { container } = render(
      <ThemeProvider theme={darkTheme}>
        <AgentMessage 
          index={1} 
          message={message} 
          onCellSelect={mockOnCellSelect} 
          onEditingChange={mockOnEditingChange}
          onUpdateMessageInput={mockOnUpdateMessageInput}
          parentMessage={parentMessage}
          selectedCellId={message.current_id}
        />
      </ThemeProvider>
    );
    
    // First, we need to actually put the component in edit mode
    // Find and click the edit button to enter edit mode
    const editButton = screen.getByRole('button', { name: /edit/i });
    fireEvent.click(editButton);
    
    // Clear the mock calls from the edit button click
    mockOnCellSelect.mockClear();
    
    // Try all navigation keys while in editing mode
    fireEvent.keyDown(document, { key: "ArrowUp" });
    fireEvent.keyDown(document, { key: "ArrowDown" });
    fireEvent.keyDown(document, { key: "ArrowLeft" });
    fireEvent.keyDown(document, { key: "ArrowRight" });
    fireEvent.keyDown(document, { key: "w" });
    fireEvent.keyDown(document, { key: "a" });
    fireEvent.keyDown(document, { key: "s" });
    fireEvent.keyDown(document, { key: "d" });
    
    act(() => { jest.runAllTimers(); });
    
    // Navigation should be blocked when editing - onCellSelect should not be called
    expect(mockOnCellSelect).not.toHaveBeenCalled();
    
    // Test that Escape key cancels editing
    fireEvent.keyDown(document, { key: "Escape" });
    expect(mockOnEditingChange).toHaveBeenCalledWith(false);
  });

  test("navigation doesn't work when component is not selected", () => {
    render(
      <ThemeProvider theme={darkTheme}>
        <AgentMessage 
          index={1} 
          message={message} 
          onCellSelect={mockOnCellSelect} 
          parentMessage={parentMessage}
          selectedCellId="different_cell_id" // Different ID means component is not selected
        />
      </ThemeProvider>
    );

    // Try all navigation keys
    fireEvent.keyDown(document, { key: "ArrowUp" });
    fireEvent.keyDown(document, { key: "ArrowDown" });
    fireEvent.keyDown(document, { key: "ArrowLeft" });
    fireEvent.keyDown(document, { key: "ArrowRight" });
    act(() => { jest.runAllTimers(); });
    
    // No navigation should happen
    expect(mockOnCellSelect).not.toHaveBeenCalled();
  });

  test("nav down works when parent message is updated with new child", () => {
    // Initial parent message with 3 children
    const initialParentMessage = {
      current_id: "parent_id",
      current_children: [
        { current_id: "child1" },
        { current_id: "child2" },
        { current_id: "child3" }
      ]
    };
  
    // Render with the initial parent message
    const { rerender } = render(
      <ThemeProvider theme={darkTheme}>
        <AgentMessage 
          index={2}  // Rendering the third child, so index is 2
          message={{ ...message, current_id: "child3" }}  // Using child3 as the current message
          onCellSelect={mockOnCellSelect} 
          parentMessage={initialParentMessage}
          selectedCellId={"child3"}
        />
      </ThemeProvider>
    );
  
    // Initially, there should be no child after child3
    fireEvent.keyDown(document, { key: "ArrowDown" });
    act(() => {
      jest.runAllTimers();
    });
    
    // Should not call onCellSelect since there's no next child yet
    expect(mockOnCellSelect).not.toHaveBeenCalled();
    
    // Now create an updated parent message with a new child
    const updatedParentMessage = {
      current_id: "parent_id",
      current_children: [
        { current_id: "child1" },
        { current_id: "child2" },
        { current_id: "child3" },
        { current_id: "child4" }  // New child added
      ]
    };
    
    // Rerender the component with the updated parent message
    rerender(
      <ThemeProvider theme={darkTheme}>
        <AgentMessage 
          index={2}  // Still the third child
          message={{ ...message, current_id: "child3" }}
          onCellSelect={mockOnCellSelect} 
          parentMessage={updatedParentMessage}  // Updated parent with new child
          selectedCellId={"child3"}
        />
      </ThemeProvider>
    );
    
    // Clear any previous calls
    mockOnCellSelect.mockClear();
    
    // Try navigating down again
    fireEvent.keyDown(document, { key: "ArrowDown" });
    act(() => {
      jest.runAllTimers();
    });
  
    // Now it should select the new child
    expect(mockOnCellSelect).toHaveBeenCalledWith("child4");
  });
});