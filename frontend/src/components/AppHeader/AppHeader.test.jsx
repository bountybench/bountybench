import '@testing-library/jest-dom/extend-expect';
import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router'; // Import MemoryRouter to provide routing context
import { AppHeader } from './AppHeader';

describe('AppHeader Component', () => {

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders app title', () => {
    render(
      <MemoryRouter>
        <AppHeader />
      </MemoryRouter>
    );
    expect(screen.getByText(/Workflow Agent/i)).toBeInTheDocument();
  });

  test('displays workflow status, phase, and model name', async () => {
    const allModels = [{ name: "model1/name", description: "model1/model_name" }];
    
    global.fetch = jest.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve({ allModels }),
      })
    );
  
    await act(async () => {
      render(
        <MemoryRouter>
          <AppHeader
            selectedWorkflow={{ id: 1, model: "model1/name" }}
            workflowStatus="Running"
            currentPhase={{ phase_id: 'Phase 1' }}
          />
        </MemoryRouter>
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

  test('interactive mode toggle works', async () => {
    const toggleMock = jest.fn();
  
    render(
      <MemoryRouter>
        <AppHeader
          onInteractiveModeToggle={toggleMock}
          interactiveMode={true}
          selectedWorkflow={{ id: 1, model: "model1/name" }}
        />
      </MemoryRouter>
    );
  
    // Wait for the checkboxes to be available
    const checkboxes = await screen.findAllByRole('checkbox');
  
    const interactiveSwitch = checkboxes[0];
  
    fireEvent.click(interactiveSwitch);
    expect(toggleMock).toHaveBeenCalled();
  });

  test('model change', async () => {
    const allModels = [
      { name: "model1/name", description: "model1/name" },
      { name: "model1/name2", description: "model1/name2" },
      { name: "model2/name1", description: "model2/name1" },
    ];
    global.fetch = jest.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve({ allModels }),
      })
    );
  
    await act(async () => {
      render(
        <MemoryRouter>
          <AppHeader
            selectedWorkflow={{ id: 1, model: "model1/name" }}
            workflowStatus="Running"
            currentPhase={{ phase_id: 'Phase 1' }}
          />
        </MemoryRouter>
      );
    });
  
    expect(global.fetch).toHaveBeenCalledTimes(1);
  
    // Wait for model name dropdown to be available before interacting
    await waitFor(() => expect(screen.getByText('name')).toBeInTheDocument());
  
    // Change model name
    fireEvent.mouseDown(screen.getByText('name'));
    await waitFor(() => fireEvent.click(screen.getByText('name2')));
  
    // Change model type
    fireEvent.mouseDown(screen.getByText('model1'));
    await waitFor(() => fireEvent.click(screen.getByText('model2')));
  });
});