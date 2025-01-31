import '@testing-library/jest-dom/extend-expect';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AppHeader } from './AppHeader';

test('renders app title', () => {
  render(<AppHeader />);
  expect(screen.getByText(/Workflow Agent/i)).toBeInTheDocument();
});

test('displays workflow status and phase', async () => {
  render(
    <AppHeader
      selectedWorkflow={{ id: 1 }}
      workflowStatus="Running"
      currentPhase={{ phase_id: 'Phase 1' }}
    />
  );

  await waitFor(() => {
    expect(screen.getByText(/Status:/i)).toBeInTheDocument();
    expect(screen.getByText(/Running/i)).toBeInTheDocument();
    expect(screen.getByText(/Phase:/i)).toBeInTheDocument();
    expect(screen.getByText(/Phase 1/i)).toBeInTheDocument();
  });
});

test('interactive mode toggle works', () => {
  const toggleMock = jest.fn();
  render(
    <AppHeader
      onInteractiveModeToggle={toggleMock}
      interactiveMode={true}
      selectedWorkflow={{ id: 1 }}
    />
  );
  const switchElement = screen.getByRole('checkbox');
  fireEvent.click(switchElement);
  expect(toggleMock).toHaveBeenCalled();
});