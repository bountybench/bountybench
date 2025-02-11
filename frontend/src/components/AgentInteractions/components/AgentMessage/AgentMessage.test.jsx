import '@testing-library/jest-dom/extend-expect'; 
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import AgentMessage from '../AgentMessage/AgentMessage';

test('renders agent type and message', () => {
  const message = {
    agent_id: 'executor_agent',
    message: "custom message",
    current_children: [],
  };
  render(<AgentMessage message={message} />);
  expect(screen.getByText(/Agent: executor_agent/i)).toBeInTheDocument();
  expect(screen.getByText(/custom message/i)).toBeInTheDocument();
});


test('checks multiple version', () => {
  const message = {
    agent_id: "agent1",
    message: "custom message",
    current_children: [],
    current_id: "message1",
    versions: ["message1", "message2"],
    version_next: "example",
  };
  render(<AgentMessage message={message}/>);
  // Verify the version text
  const versionText = screen.getByText(`${1}/${2}`);
  expect(versionText).toBeInTheDocument();

  // Verify the back arrow button present and is disabled
  const backButton = screen.getByRole('button', { name: /arrow back/i }); 
  expect(backButton).toBeInTheDocument();
  expect(backButton).toBeDisabled();

  // Verify the forward arrow button is enabled
  const forwardButton = screen.getByRole('button', { name: /arrow forward/i }); 
  expect(forwardButton).toBeInTheDocument();
  expect(forwardButton).not.toBeDisabled();
});


test('triggers version change', () => {
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

  // Render the AgentMessage component with necessary props
  render(<AgentMessage message={message} onCellSelect={mockOnCellSelect} onToggleVersion={mockOnToggleVersion} />);

  // Click the forward arrow to trigger version change
  fireEvent.click(screen.getByRole('button', { name: /arrow forward/i }));
  
  // Assert that the onToggleVersion was called with the correct parameters
  expect(mockOnToggleVersion).toHaveBeenCalledWith('message1', 'next');
});
