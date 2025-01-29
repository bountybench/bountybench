import '@testing-library/jest-dom/extend-expect';
import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { AppHeader } from './AppHeader';

describe('Appheader Component', () => {

  beforeEach(() => {
    jest.clearAllMocks();
  });

test('renders app title', () => {
  render(<AppHeader />);
  expect(screen.getByText(/Workflow Agent/i)).toBeInTheDocument();
});

test('displays workflow status, phase, and model name', async () => {
  const allModels = { 'model1/name' : 'model1/name' };
  global.fetch = jest.fn(() =>
    Promise.resolve({
      json: () => Promise.resolve({ allModels })
    })
  );

  await act(async () => {
      render(<AppHeader
      selectedWorkflow={{ id: 1, model: "model1/name" }}
      workflowStatus="Running"
      currentPhase={{ phase_id: 'Phase 1' }}
    />
  );
  });

  expect(global.fetch).toHaveBeenCalledTimes(1);
  
  await waitFor(() => {
    expect(screen.getByText(/Status:/i)).toBeInTheDocument();
    expect(screen.getByText(/Running/i)).toBeInTheDocument();
    expect(screen.getByText(/Phase:/i)).toBeInTheDocument();
    expect(screen.getByText(/Phase 1/i)).toBeInTheDocument();
    expect(screen.getByText(/model1/i)).toBeInTheDocument();
    expect(screen.getByText(/name/i)).toBeInTheDocument();
  });
});

test('interactive mode toggle works', () => {
  const all_models = { "model1/name" : "model1/model_name" };
  global.fetch = jest.fn(() =>
    Promise.resolve({
      json: () => Promise.resolve({ all_models })
    })
  );
  const toggleMock = jest.fn();
  render(
    <AppHeader
      onInteractiveModeToggle={toggleMock}
      interactiveMode={true}
      selectedWorkflow={{ id: 1, model: "model1/name" }}
    />
  );
  const switchElement = screen.getByRole('checkbox');
  fireEvent.click(switchElement);
  expect(toggleMock).toHaveBeenCalled();
});

test('model change', async () => {
  const allModels = { 'model1/name' : 'model1/name', 'model1/name2' : 'model1/name2', 'model2/name1' : 'model2/name1'};
  global.fetch = jest.fn(() =>
    Promise.resolve({
      json: () => Promise.resolve({ allModels })
    })
  );

  await act(async () => {
      render(<AppHeader
      selectedWorkflow={{ id: 1, model: "model1/name" }}
      workflowStatus="Running"
      currentPhase={{ phase_id: 'Phase 1' }}
    />
  );
  });

  expect(global.fetch).toHaveBeenCalledTimes(1);

  // Change model name
  fireEvent.mouseDown(screen.getByText('name'));
  fireEvent.click(screen.getByText('name2'));

  // Change model type
  fireEvent.mouseDown(screen.getByText('model1'));
  fireEvent.click(screen.getByText('model2'));
});
});