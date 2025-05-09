import "@testing-library/jest-dom/extend-expect";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AgentMessage from "../AgentMessage/AgentMessage";
import { ThemeProvider } from "@mui/material/styles";
import { darkTheme } from "../../../../theme";

test("renders agent type and message", () => {
	const message = {
		agent_id: "executor_agent",
		message: "custom message",
		current_children: [],
	};
	render(
		<ThemeProvider theme={darkTheme}>
      <AgentMessage
        message={message}
        registerToggleOperation={() => { }}
      />
		</ThemeProvider>
	);
	expect(screen.getByText(/EXECUTOR_AGENT/i)).toBeInTheDocument();
	expect(screen.getByText(/custom message/i)).toBeInTheDocument();
});

test("checks multiple version", () => {
  const message = {
    agent_id: "agent1",
    message: "custom message",
    current_children: [],
    current_id: "message1",
    versions: ["message1", "message2"],
    version_next: "example",
  };
  render(
    <ThemeProvider theme={darkTheme}>
      <AgentMessage
        message={message}
        registerToggleOperation={() => { }}
      />
    </ThemeProvider>
  );
  // Verify the version text
  // const versionText = screen.getByText(`${1}/${2}`);
  // expect(versionText).toBeInTheDocument();

  // Verify the back arrow button present and is disabled
  const backButton = screen.getByRole("button", { name: /arrow back/i });
  expect(backButton).toBeInTheDocument();
  expect(backButton).toBeDisabled();

  // Verify the forward arrow button is enabled
  const forwardButton = screen.getByRole("button", { name: /arrow forward/i });
  expect(forwardButton).toBeInTheDocument();
  expect(forwardButton).not.toBeDisabled();
});

test("triggers version change", () => {
  const message = {
    agent_id: "agent1",
    message: "custom message",
    current_children: [],
    current_id: "message1",
    versions: ["message1", "message2"],
    version_next: "example",
  };

  const mockOnToggleVersion = jest.fn();
  const mockOnCellSelect = jest.fn();
  const mockRegisterToggleOperation = jest.fn();

  // Render the AgentMessage component with necessary props
  render(
    <ThemeProvider theme={darkTheme}>
      <AgentMessage
        message={message}
        onCellSelect={mockOnCellSelect}
        onToggleVersion={mockOnToggleVersion}
        registerToggleOperation={mockRegisterToggleOperation}
      />
    </ThemeProvider>
  );

  // Click the forward arrow to trigger version change
  fireEvent.click(screen.getByRole("button", { name: /arrow forward/i }));

  // Assert that registerToggleOperation was called with the correct parameters
  expect(mockRegisterToggleOperation).toHaveBeenCalledWith("message1", "example", "next");

  // Assert that the onToggleVersion was called with the correct parameters
  expect(mockOnToggleVersion).toHaveBeenCalledWith("message1", "next");
});