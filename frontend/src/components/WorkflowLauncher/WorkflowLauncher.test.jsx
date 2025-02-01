import React from 'react';
import { BrowserRouter as Router } from 'react-router';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { WorkflowLauncher } from './WorkflowLauncher';
import { useServerAvailability } from '../../hooks/useServerAvailability';

// Import jest-dom matchers
import '@testing-library/jest-dom/extend-expect';
jest.mock('react-router', () => ({
  ...jest.requireActual('react-router'),
  useNavigate: jest.fn(),
}));

// Mock the dependencies
jest.mock('../../hooks/useServerAvailability');

describe('WorkflowLauncher Component', () => {
  const onWorkflowStartMock = jest.fn();
  const setInteractiveModeMock = jest.fn();
  const navigate = jest.requireMock('react-router').useNavigate;

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders loading state while checking server availability', () => {
    useServerAvailability.mockReturnValue({ isServerAvailable: false, isChecking: true });

    render(<Router><WorkflowLauncher onWorkflowStart={onWorkflowStartMock} interactiveMode={true} setInteractiveMode={setInteractiveModeMock} /></Router>);

    expect(screen.getByText('Checking server availability...')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  test('renders an alert if the server is not available', () => {
    useServerAvailability.mockReturnValue({ isServerAvailable: false, isChecking: false });

    render(<Router><WorkflowLauncher onWorkflowStart={onWorkflowStartMock} interactiveMode={true} setInteractiveMode={setInteractiveModeMock} /></Router>);

    expect(screen.getByText('Cannot reach server. Retrying...')).toBeInTheDocument();
  });
  
  test('fetches and displays workflows when the server is available', async () => {
    useServerAvailability.mockReturnValue({ isServerAvailable: true, isChecking: false });
    const workflows = [
      { name: 'Workflow 1', description: 'Description 1' },
      { name: 'Workflow 2', description: 'Description 2' }
    ];
    global.fetch = jest.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve({ workflows })
      })
    );

    await act(async () => {
      render(<Router><WorkflowLauncher onWorkflowStart={onWorkflowStartMock} interactiveMode={true} setInteractiveMode={setInteractiveModeMock} /></Router>);
    });

    // Fetches both workflows and models
    expect(global.fetch).toHaveBeenCalledTimes(3);

    // Wait for async state updates to complete
    await waitFor(() => {
      expect(screen.getByText(/Start New Workflow/i)).toBeInTheDocument();
    });

    // Verify the workflow items are present
    fireEvent.mouseDown(screen.getByLabelText(/Workflow Type/i));

    const workflow1 = await screen.findByText('Workflow 1');
    const description1 = await screen.findByText('Description 1');
    const workflow2 = await screen.findByText('Workflow 2');
    const description2 = await screen.findByText('Description 2');

    expect(workflow1).toBeInTheDocument();
    expect(description1).toBeInTheDocument();
    expect(workflow2).toBeInTheDocument();
    expect(description2).toBeInTheDocument();
  });
  
  test('displays an error message if fetching workflows fails', async () => {
    useServerAvailability.mockReturnValue({ isServerAvailable: true, isChecking: false });
    global.fetch = jest.fn(() => Promise.reject(new Error('Failed to fetch workflows')));
  
    // Mock console.error
    const consoleErrorMock = jest.spyOn(console, 'error').mockImplementation(jest.fn());
  
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
  
    expect(global.fetch).toHaveBeenCalledTimes(3);
  
    // Wait for async state updates to complete
    await waitFor(() => {
      expect(consoleErrorMock).toHaveBeenCalledWith('Failed to fetch workflows. Make sure the backend server is running.');
    });
  
    // Restore console.error after the test
    consoleErrorMock.mockRestore();
  });

  test('handles form input correctly, submits the form successfully, and navigates to new page', async () => {
    useServerAvailability.mockReturnValue({ isServerAvailable: true, isChecking: false });
    const workflows = [{ name: 'Workflow 1', description: 'Description 1' }];
    const helmModels = [{ name: 'model1', description: 'Description 1' }];
    const apiKeys = { HELM_API_KEY: 'mock-api-key' };
    global.fetch = jest
      .fn()
      .mockImplementationOnce(() =>
        Promise.resolve({
          json: () => Promise.resolve({ workflows }) // First fetch API call (fetchWorkflows)
        })
      )
      .mockImplementationOnce(() =>
        Promise.resolve({
          json: () => Promise.resolve(apiKeys) // Second fetch API call (fetchApiKeys)
        })
      )
      .mockImplementationOnce(() =>
        Promise.resolve({
          json: () => Promise.resolve({ helmModels })
        })
      )
      .mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ workflow_id: '123', model: "test_model" })
        })
      );

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

    expect(global.fetch).toHaveBeenCalledTimes(3);

    // Ensure form is updated and submitted correctly
    fireEvent.mouseDown(screen.getByLabelText(/Workflow Type/i));
    fireEvent.click(screen.getByText('Workflow 1'));

    fireEvent.change(screen.getByLabelText(/Task Repository Directory/i), { target: { value: 'test-dir' } });
    fireEvent.change(screen.getByLabelText(/Bounty Number/i), { target: { value: '123' } });
    fireEvent.change(screen.getByLabelText(/Iterations \(per phase\)/i), { target: { value: '5' } });


    fireEvent.mouseDown(screen.getByLabelText(/Model Type/i));
    fireEvent.click(screen.getByText('HELM'));

    fireEvent.mouseDown(screen.getByLabelText(/Model Name/i));
    fireEvent.click(screen.getByText('model1'));

    // Submit form
    fireEvent.click(screen.getByRole('button', { name: /Start Workflow/i }));

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(4));
    expect(onWorkflowStartMock).toHaveBeenCalledWith('123', "test_model", true);
  });

  test('displays an error message if the form submission fails', async () => {
    useServerAvailability.mockReturnValue({ isServerAvailable: true, isChecking: false });
    const workflows = [{ name: 'Workflow 1', description: 'Description 1' }];
    const helmModels = [{ name: 'model1', description: 'Description 1' }];
    const apiKeys = { HELM_API_KEY: 'mock-api-key' };
    global.fetch = jest
      .fn()
      .mockImplementationOnce(() =>
        Promise.resolve({
          json: () => Promise.resolve({ workflows }) // First fetch API call (fetchWorkflows)
        })
      )
      .mockImplementationOnce(() =>
        Promise.resolve({
          json: () => Promise.resolve(apiKeys) // Second fetch API call (fetchApiKeys)
        })
      )
      .mockImplementationOnce(() =>
        Promise.resolve({
          json: () => Promise.resolve({ helmModels })
        })
      )
      .mockImplementationOnce(() =>
        Promise.resolve({
          ok: false,
          json: () => Promise.resolve({ error: 'Failed to start workflow' })
        })
      );
  
    // Mock console.error
    const consoleErrorMock = jest.spyOn(console, 'error').mockImplementation(jest.fn());
  
    await act(async () => {
      render(
        <Router>
          <WorkflowLauncher 
            onWorkflowStart={onWorkflowStartMock} 
            interactiveMode={false} 
            setInteractiveMode={setInteractiveModeMock} 
          />
        </Router>
      );
    });
  
    expect(global.fetch).toHaveBeenCalledTimes(3);
  
    // Open the select dropdown and select the option
    fireEvent.mouseDown(screen.getByLabelText(/Workflow Type/i));
    fireEvent.click(screen.getByText(/Workflow 1/i));
  
    fireEvent.change(screen.getByLabelText(/Task Repository Directory/i), { target: { value: 'test-dir' } });
    fireEvent.change(screen.getByLabelText(/Bounty Number/i), { target: { value: '123' } });
    fireEvent.change(screen.getByLabelText(/Iterations \(per phase\)/i), { target: { value: '5' } });
    
    fireEvent.mouseDown(screen.getByLabelText(/Model Type/i));
    fireEvent.click(screen.getByText('Non-HELM'));

    // Submit form
    fireEvent.click(screen.getByRole('button', { name: /Start Workflow/i }));
  
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(4));
  
    // Check if console.error was called with the expected error message
    expect(consoleErrorMock).toHaveBeenCalledWith('Failed to start workflow');
  
    // Restore console.error after the test
    consoleErrorMock.mockRestore();
  });
});