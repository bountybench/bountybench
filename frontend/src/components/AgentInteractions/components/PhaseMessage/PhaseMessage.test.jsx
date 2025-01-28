import '@testing-library/jest-dom/extend-expect'; 
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import PhaseMessage from './PhaseMessage';

test('renders phase title and summary', () => {
  const message = {
    phase_name: 'Exploit Phase',
    phase_summary: 'Testing phase summary.',
    current_children: [],
  };
  render(<PhaseMessage message={message} />);
  expect(screen.getByText(/Phase: Exploit Phase/i)).toBeInTheDocument();
  expect(screen.getByText(/Summary: Testing phase summary/i)).toBeInTheDocument();
});

test('toggles content visibility', async () => {
  const message = {
    phase_name: 'Exploit Phase',
    phase_summary: 'Testing phase summary',
    current_children: [],
  };
  render(<PhaseMessage message={message} />);
  
  const toggleButton = screen.getByRole('button', { name: /toggle phase content/i });
  const parentDiv = screen.getByText(/Summary: Testing phase summary/i).parentElement.parentElement.parentElement;
  
  // Ensure initial state is expanded and height is not 0
  expect(parentDiv).not.toHaveStyle({ height: '0px' });
  
  // Click to collapse
  fireEvent.click(toggleButton);
  await waitFor(() => {
    expect(parentDiv).toHaveStyle({ height: '0px' });
  });
  
  // Click again to expand
  fireEvent.click(toggleButton);
  await waitFor(() => {
    expect(parentDiv).not.toHaveStyle({ height: '0px' });
  });
});

test('renders agent messages', () => {
  const message = {
    phase_name: 'Exploit Phase',
    phase_summary: 'Testing phase summary',
    current_children: [{ message: 'Agent message content' }],
  };
  render(<PhaseMessage message={message} />);
  expect(screen.getByText(/Agent Messages:/i)).toBeInTheDocument();
  expect(screen.getByText(/Agent message content/i)).toBeInTheDocument();
});