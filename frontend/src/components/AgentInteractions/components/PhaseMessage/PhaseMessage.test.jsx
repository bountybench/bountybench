import "@testing-library/jest-dom/extend-expect";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import PhaseMessage from "./PhaseMessage";
import { ThemeProvider } from "@mui/material";
import { darkTheme } from "../../../../theme";

test("renders phase title and summary", () => {
	const message = {
		phase_name: "Exploit Phase",
		phase_summary: "Testing phase summary.",
		current_children: [],
	};
	render(<PhaseMessage message={message} />);
	expect(screen.getByText(/Phase: Exploit Phase/i)).toBeInTheDocument();
	expect(screen.getByText(/Summary: Testing phase summary/i)).toBeInTheDocument();
});

test("toggles content visibility", async () => {
	const message = {
		phase_name: "Exploit Phase",
		phase_summary: "Testing phase summary",
		current_children: [],
	};
	render(<PhaseMessage message={message} />);

	const toggleButton = screen.getByRole("button", { name: /toggle phase content/i });
	const parentDiv = screen.getByText(/Summary: Testing phase summary/i).parentElement.parentElement.parentElement;

	// Ensure initial state is expanded and height is not 0
	expect(parentDiv).not.toHaveStyle({ height: "0px" });

	// Click to collapse
	fireEvent.click(toggleButton);
	await waitFor(() => {
		expect(parentDiv).toHaveStyle({ height: "0px" });
	});

	// Click again to expand
	fireEvent.click(toggleButton);
	await waitFor(() => {
		expect(parentDiv).not.toHaveStyle({ height: "0px" });
	});
});

test('handles updating action input', async () => {
    const mockOnCellSelect = jest.fn(); // Mock function for onCellSelect
    const message = {
      phase_name: 'Exploit Phase',
      phase_summary: 'Testing phase summary',
      agent_messages: [
        {
          agent_id: 'system',
          current_id: 'agent-11',
          message: 'Old Message 1',
          action_messages: [],
          current_children: [],
          message_type: 'AgentMessage',
        },
        {
          agent_id: 'agent',
          current_id: 'agent-21',
          message: 'Old Message 2',
          action_messages: [{current_id: 'action-11', message: 'former1'},{current_id: 'action-21', message: 'former2'}],
          current_children: [{current_id: 'action-11', message: 'former1'},{current_id: 'action-21', message: 'former2'}],
          message_type: 'AgentMessage',
        },
        {
          agent_id: 'system',
          current_id: 'agent-12',
          message: 'New Message 1',
          action_messages: [],
          current_children: [],
          message_type: 'AgentMessage',
        },
        {
          agent_id: 'agent',
          current_id: 'agent-22',
          message: 'New Message 2',
          action_messages: [{current_id: 'action-12', message: 'current1'},{current_id: 'action-22', message: 'current2'}],
          current_children: [{current_id: 'action-12', message: 'current1'},{current_id: 'action-22', message: 'current2'}],
          message_type: 'AgentMessage',
        },
      ],
      current_children: [{
          agent_id: 'system',
          current_id: 'agent-12',
          message: 'New Message 1',
          action_messages: [],
          current_children: [],
          message_type: 'AgentMessage',
        },
        {
          agent_id: 'agent',
          current_id: 'agent-22',
          message: 'New Message 2',
          action_messages: [{current_id: 'action-12', message: 'current1'},{current_id: 'action-22', message: 'current2'}],
          current_children: [{current_id: 'action-12', message: 'current1'},{current_id: 'action-22', message: 'current2'}],
          message_type: 'AgentMessage',
        },
      ],
    };
    render(<PhaseMessage message={message} onCellSelect={mockOnCellSelect}/>);
    // Checks that the newest version is displayed
    expect(await screen.findByText(/Agent: system/i)).toBeInTheDocument();
    expect(await screen.findByText(/New Message 1/i)).toBeInTheDocument();
    expect(await screen.findByText(/current1/i)).toBeInTheDocument();
    expect(await screen.findByText(/current2/i)).toBeInTheDocument();

    // Verify the version text (1/2)
      const versionText = screen.getByText(`${2}/${2}`);
      expect(versionText).toBeInTheDocument();
    
      // Verify the version toggling buttons are present
      const backButton = screen.getByRole('button', { name: /arrow back/i }); 
      const forwardButton = screen.getByRole('button', { name: /arrow forward/i }); 
      expect(forwardButton).toBeInTheDocument();
      expect(forwardButton).toBeDisabled();
      expect(backButton).toBeInTheDocument();
      expect(backButton).not.toBeDisabled();
    
      // Select previous version and verify that the display is changed
      fireEvent.click(backButton);
      expect(screen.getByText(/former1/i)).toBeInTheDocument();
      expect(screen.getByText(/former2/i)).toBeInTheDocument();
      const newVersionText = screen.getByText(`${1}/${2}`);
      expect(newVersionText).toBeInTheDocument();

});
