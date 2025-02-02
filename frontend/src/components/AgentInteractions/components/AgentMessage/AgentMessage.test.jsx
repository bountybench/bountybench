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


test('checks multiple version', () => {
  const message = {
    agent_id: "agent1",
    message: "custom message",
    current_children: [],
  };
  render(<AgentMessage message={message} phaseDisplayedIndex={1} phaseVersionLength={2}/>);
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
  };
  const mockPhaseChildUpdate = jest.fn();
  render(<AgentMessage index={0} message={message} onPhaseChildUpdate={mockPhaseChildUpdate} phaseDisplayedIndex={1} phaseVersionLength={2}/>);
  fireEvent.click(screen.getByRole('button', { name: /arrow forward/i }));
  // Version index is incremented by 1
  expect(mockPhaseChildUpdate).toHaveBeenCalledWith('agent1', 1);
});


test('multiple versions of action messages', () => {
  const message = {
    agent_id: 'agent-1',
    current_id: 'agent-1',
    message: 'agent message',
    action_messages: [{current_id: 'action-11', message: 'former1'},{current_id: 'action-21', message: 'former2'}, {current_id: 'action-12', message: 'current1'},{current_id: 'action-22', message: 'current2'}],
    current_children: [{current_id: 'action-12', message: 'current1'},{current_id: 'action-22', message: 'current2'}],
    message_type: 'AgentMessage',
  };

  render(<AgentMessage index={0} message={message}/>);
  
  expect(screen.getByText(/former1/i)).toBeInTheDocument();
  expect(screen.getByText(/former2/i)).toBeInTheDocument();

  // Verify the version text (1/2)
  const versionText = screen.getByText(`${1}/${2}`);
  expect(versionText).toBeInTheDocument();

  // Verify the version toggling buttons are present
  const backButton = screen.getByRole('button', { name: /arrow back/i }); 
  const forwardButton = screen.getByRole('button', { name: /arrow forward/i }); 
  expect(forwardButton).toBeInTheDocument();
  expect(forwardButton).not.toBeDisabled();
  expect(backButton).toBeInTheDocument();
  expect(backButton).toBeDisabled();

  // Select previous version and verify that the display is changed
  fireEvent.click(forwardButton);
  expect(screen.getByText(/current1/i)).toBeInTheDocument();
  expect(screen.getByText(/current2/i)).toBeInTheDocument();
  const newVersionText = screen.getByText(`${2}/${2}`);
  expect(newVersionText).toBeInTheDocument();

});
