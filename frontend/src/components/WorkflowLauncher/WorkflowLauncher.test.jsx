import React from 'react';
import { BrowserRouter as Router } from 'react-router';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { WorkflowLauncher } from './WorkflowLauncher';
import { useServerAvailability } from '../../hooks/useServerAvailability';

// Import jest-dom matchers
import '@testing-library/jest-dom/extend-expect';
const mockNavigate = jest.fn();

jest.mock('react-router', () => ({
  ...jest.requireActual('react-router'),
  useNavigate: () => mockNavigate,
}));

// Mock the dependencies
jest.mock('../../hooks/useServerAvailability', () => ({
  useServerAvailability: jest.fn(),
}));

describe('WorkflowLauncher Component', () => {
  const onWorkflowStartMock = jest.fn();
  const setInteractiveModeMock = jest.fn();
  const mockNavigate = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn();
  });

  test('renders checking server state while server availability is being checked', () => {
    useServerAvailability.mockReturnValue({ isAvailable: false, isChecking: true, error: null });

    render(<Router><WorkflowLauncher onWorkflowStart={onWorkflowStartMock} interactiveMode={true} setInteractiveMode={setInteractiveModeMock} /></Router>);

    expect(screen.getByText('Checking server availability...')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  test('renders an alert if the server is not available', () => {
    useServerAvailability.mockReturnValue({ isAvailable: false, isChecking: false, error: "Server is not responding" });

    render(<Router><WorkflowLauncher onWorkflowStart={onWorkflowStartMock} interactiveMode={true} setInteractiveMode={setInteractiveModeMock} /></Router>);

    expect(screen.getByText('Server is not responding')).toBeInTheDocument();
  });

  test('sets launcher state to LOADING_DATA when server is available', async () => {
    let serverAvailabilityValue = {
      isAvailable: false,
      isChecking: true,
      error: null
    };

    useServerAvailability.mockImplementation(() => serverAvailabilityValue);

    global.fetch
      .mockResolvedValueOnce({ json: () => Promise.resolve({ workflows: [] }) })
      .mockResolvedValueOnce({ json: () => Promise.resolve({}) })
      .mockResolvedValueOnce({ json: () => Promise.resolve({ helmModels: [], nonHelmModels: [] }) });

    render(
      <Router>
        <WorkflowLauncher 
          onWorkflowStart={onWorkflowStartMock} 
          interactiveMode={true} 
          setInteractiveMode={setInteractiveModeMock} 
        />
      </Router>
    );

    expect(screen.getByText('Checking server availability...')).toBeInTheDocument();

    act(() => {
      serverAvailabilityValue = {
        isAvailable: true,
        isChecking: false,
        error: null
      };
      useServerAvailability.mockImplementation(() => serverAvailabilityValue);
    });

    // Force a re-render
    render(
      <Router>
        <WorkflowLauncher 
          onWorkflowStart={onWorkflowStartMock} 
          interactiveMode={true} 
          setInteractiveMode={setInteractiveModeMock} 
        />
      </Router>
    );

    await waitFor(() => {
      expect(screen.getByText('Loading workflows...')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText(/Start New Workflow/i)).toBeInTheDocument();
    });

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(3));
  });

  test('fetches and displays workflows when the server is available', async () => {
    useServerAvailability.mockReturnValue({ isAvailable: true, isChecking: false, error: null });

    const workflows = [
      { name: 'Workflow 1', description: 'Description 1' },
      { name: 'Workflow 2', description: 'Description 2' }
    ];
    const apiKeys = { HELM_API_KEY: 'mock-api-key' };
    const models = { helmModels: [], nonHelmModels: [] };
    
    global.fetch
      .mockResolvedValueOnce({ json: () => Promise.resolve({ workflows }) })
      .mockResolvedValueOnce({ json: () => Promise.resolve(apiKeys) })
      .mockResolvedValueOnce({ json: () => Promise.resolve(models) });

    await act(async () => {
      render(
        <Router>
          <WorkflowLauncher 
            onWorkflowStart={onWorkflowStartMock} 
            interactiveMode={true} 
            setInteractiveMode={setInteractiveModeMock} 
          />
        </Router>
      );
    });

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(3));

    expect(screen.getByText(/Start New Workflow/i)).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByLabelText(/Workflow Type/i));

    await waitFor(() => {
      expect(screen.getAllByText('Workflow 1')).toHaveLength(2); // One for selected and one for in list
      expect(screen.getAllByText('Description 1')).toHaveLength(2);
      expect(screen.getByText('Workflow 2')).toBeInTheDocument();
      expect(screen.getByText('Description 2')).toBeInTheDocument();
    });
  });

  test('handles form input correctly, submits the form successfully, and navigates to new page', async () => {
    useServerAvailability.mockReturnValue({ isAvailable: true, isChecking: false, error: null });
  
    const workflows = [
      { name: 'Workflow 1', description: 'Description 1' },
      { name: 'Workflow 2', description: 'Description 2' }
    ];
    const apiKeys = { HELM_API_KEY: 'mock-api-key' };
    const models = { 
      helmModels: [{ name: 'model1', description: 'Description 1' }, { name: 'model3', description: 'Description 3' }],
      nonHelmModels: [{ name: 'model2', description: 'Description 2' }]
    };
    
    global.fetch = jest.fn()
      .mockResolvedValueOnce({ json: () => Promise.resolve({ workflows }) })
      .mockResolvedValueOnce({ json: () => Promise.resolve(apiKeys) })
      .mockResolvedValueOnce({ json: () => Promise.resolve(models) })
      .mockResolvedValueOnce({ 
        ok: true, 
        json: () => Promise.resolve({ workflow_id: '123', model: "test_model" })
      });
  
    await act(async () => {
      render(
        <Router>
          <WorkflowLauncher 
            onWorkflowStart={onWorkflowStartMock} 
            interactiveMode={true} 
            setInteractiveMode={setInteractiveModeMock} 
          />
        </Router>
      );
    });
  
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(3));
  
    const workflowTypeSelect = screen.getByRole('combobox', { name: "Workflow Type" });
    fireEvent.mouseDown(workflowTypeSelect);

    await waitFor(() => {
      expect(screen.getAllByText('Workflow 1')).toHaveLength(2); // One for selected and one for in list
      expect(screen.getAllByText('Description 1')).toHaveLength(2);
      expect(screen.getByText('Workflow 2')).toBeInTheDocument();
      expect(screen.getByText('Description 2')).toBeInTheDocument();
    });
  
    fireEvent.click(screen.getByText('Workflow 2'));
  
    fireEvent.change(screen.getByLabelText(/Task Repository Directory/i), { target: { value: 'test-dir' } });
    fireEvent.change(screen.getByLabelText(/Bounty Number/i), { target: { value: '123' } });
    fireEvent.change(screen.getByLabelText(/Iterations \(per phase\)/i), { target: { value: '5' } });
  
    const modelTypeSelect = screen.getByRole('combobox', { name: /Model Type/i });
    fireEvent.mouseDown(modelTypeSelect);
    fireEvent.click(screen.getByText('HELM'));
  
    const modelNameSelect = screen.getByRole('combobox', { name: /Model Name/i });
    fireEvent.mouseDown(modelNameSelect);
    fireEvent.click(screen.getByText('model3'));
  
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Start Workflow/i }));
    });
  
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(4));
    await waitFor(() => expect(onWorkflowStartMock).toHaveBeenCalledWith('123', "test_model", true));
  });

  test('displays an error message if the form submission fails', async () => {
    useServerAvailability.mockReturnValue({ isAvailable: true, isChecking: false, error: null });
  
    const workflows = [
      { name: 'Workflow 1', description: 'Description 1' },
      { name: 'Workflow 2', description: 'Description 2' }
    ];
    const apiKeys = { HELM_API_KEY: 'mock-api-key' };
    const models = { 
      helmModels: [{ name: 'model1', description: 'Description 1' }, { name: 'model3', description: 'Description 3' }],
      nonHelmModels: [{ name: 'model2', description: 'Description 2' }]
    };
    
    global.fetch = jest.fn()
      .mockResolvedValueOnce({ json: () => Promise.resolve({ workflows }) })
      .mockResolvedValueOnce({ json: () => Promise.resolve(apiKeys) })
      .mockResolvedValueOnce({ json: () => Promise.resolve(models) })
      .mockResolvedValueOnce({ 
        ok: false, 
        json: () => Promise.resolve({ error: 'Failed to start workflow' })
      });
    
    await act(async () => {
      render(
        <Router>
          <WorkflowLauncher 
            onWorkflowStart={onWorkflowStartMock} 
            interactiveMode={true} 
            setInteractiveMode={setInteractiveModeMock} 
          />
        </Router>
      );
    });
  
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(3));
  
    const workflowTypeSelect = screen.getByRole('combobox', { name: "Workflow Type" });
    fireEvent.mouseDown(workflowTypeSelect);

    await waitFor(() => {
      expect(screen.getAllByText('Workflow 1')).toHaveLength(2); // One for selected and one for in list
      expect(screen.getAllByText('Description 1')).toHaveLength(2);
      expect(screen.getByText('Workflow 2')).toBeInTheDocument();
      expect(screen.getByText('Description 2')).toBeInTheDocument();
    });
  
    fireEvent.click(screen.getByText('Workflow 2'));
  
    fireEvent.change(screen.getByLabelText(/Task Repository Directory/i), { target: { value: 'test-dir' } });
    fireEvent.change(screen.getByLabelText(/Bounty Number/i), { target: { value: '123' } });
    fireEvent.change(screen.getByLabelText(/Iterations \(per phase\)/i), { target: { value: '5' } });
  
    const modelTypeSelect = screen.getByRole('combobox', { name: /Model Type/i });
    fireEvent.mouseDown(modelTypeSelect);
    fireEvent.click(screen.getByText('HELM'));
  
    const modelNameSelect = screen.getByRole('combobox', { name: /Model Name/i });
    fireEvent.mouseDown(modelNameSelect);
    fireEvent.click(screen.getByText('model3'));
  
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Start Workflow/i }));
    });
  
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(4));
    expect(screen.getByText('Failed to start workflow')).toBeInTheDocument();
  });
});