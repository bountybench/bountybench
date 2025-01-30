import '@testing-library/jest-dom/extend-expect'; 
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import AgentMessage from '../AgentMessage/AgentMessage';

//AgentMessage = ({ message, onUpdateActionInput, onRerunAction, onPhaseChildUpdate, phaseMultiVersion, phaseDisplayedIndex, phaseVersionLength })

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

/*
test('checks multiple version', () => {
  const message = {
    message: "custom message",
    current_children: [],
  };
  render(<AgentMessage message={message} phaseMultiVersion={true} phaseDisplayedIndex={1} phaseVersionLength={2}/>);
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
*/

test('triggers version change', () => {
  const message = {
    message: "custom message",
    current_children: [],
  };
  const mockPhaseChildUpdate = jest.fn();
  render(<AgentMessage index={0} message={message} onPhaseChildUpdate={mockPhaseChildUpdate} phaseDisplayedIndex={1} phaseVersionLength={2}/>);
  fireEvent.click(screen.getByRole('button', { name: /arrow forward/i }));
  // Version index is incremented by 1
  expect(mockPhaseChildUpdate).toHaveBeenCalledWith(1);
});
