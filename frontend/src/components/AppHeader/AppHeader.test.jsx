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
    const allModels = [{ 'name': "model1/name", 'description': "model1/model_name" }];
    global.fetch = jest.fn((url) => {
      if (url.includes('/allmodels')) {
        return Promise.resolve({
          json: () => Promise.resolve({ allModels }),
        });
      }
      if (url.includes('/max-iterations')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ max_iterations: 10 }),
        });
      }
    });

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

    expect(global.fetch).toHaveBeenCalledTimes(2);
    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/workflow/allmodels');
    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/workflow/1/max-iterations');

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
    const allModels = [{ 'name': "model1/name", 'description': "model1/model_name" }];
    global.fetch = jest.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve({ allModels }),
      })
    );
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
    const switchElement = screen.getByRole('checkbox');
    fireEvent.click(switchElement);
    expect(toggleMock).toHaveBeenCalled();
  });

  test('model change', async () => {
    const allModels = [
      { 'name': "model1/name", 'description': "model1/name" },
      { 'name': "model1/name2", 'description': "model1/name2" },
      { 'name': "model2/name1", 'description': "model2/name1" },
    ];
    global.fetch = jest.fn((url) => {
      if (url.includes('/allmodels')) {
        return Promise.resolve({
          json: () => Promise.resolve({ allModels }),
        });
      }
      if (url.includes('/max-iterations')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ max_iterations: 10 }),
        });
      }
    });

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

    expect(global.fetch).toHaveBeenCalledTimes(2);

    // Change model name
    fireEvent.mouseDown(screen.getByText('name'));
    fireEvent.click(screen.getByText('name2'));

    // Change model type
    fireEvent.mouseDown(screen.getByText('model1'));
    fireEvent.click(screen.getByText('model2'));
  });
});

describe('Max Iterations Input', () => {
  const setupMaxIterationsTest = () => {
    const onMaxIterationsChange = jest.fn();
    const allModels = [{ 'name': "model1/name", 'description': "model1/model_name" }];
    
    global.fetch = jest.fn((url) => {
      if (url.includes('/allmodels')) {
        return Promise.resolve({
          json: () => Promise.resolve({ allModels }),
        });
      }
      if (url.includes('/max-iterations')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ max_iterations: 10 }),
        });
      }
    });

    render(
      <MemoryRouter>
        <AppHeader
          selectedWorkflow={{ id: 1, model: "model1/name" }}
          onMaxIterationsChange={onMaxIterationsChange}
        />
      </MemoryRouter>
    );

    const input = screen.getByRole('spinbutton');
    return { input, onMaxIterationsChange };
  };

  test('updates local state immediately while typing', async () => {
    const { input } = setupMaxIterationsTest();
    
    fireEvent.change(input, { target: { value: '5' } });
    expect(input.value).toBe('5');
  });

  test('does not call API until Enter is pressed', async () => {
    const { input, onMaxIterationsChange } = setupMaxIterationsTest();
    
    fireEvent.change(input, { target: { value: '5' } });
    expect(onMaxIterationsChange).not.toHaveBeenCalled();

    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onMaxIterationsChange).toHaveBeenCalledWith(5);
  });

  test('corrects invalid values to 1 on blur', async () => {
    const { input, onMaxIterationsChange } = setupMaxIterationsTest();
    
    // Test with 0
    fireEvent.change(input, { target: { value: '0' } });
    fireEvent.blur(input);
    expect(input.value).toBe('1');
    expect(onMaxIterationsChange).toHaveBeenCalledWith(1);

    // Test with negative number
    fireEvent.change(input, { target: { value: '-5' } });
    fireEvent.blur(input);
    expect(input.value).toBe('1');
    expect(onMaxIterationsChange).toHaveBeenCalledWith(1);
  });

  test('allows empty value while typing but corrects on blur', async () => {
    const { input, onMaxIterationsChange } = setupMaxIterationsTest();
    
    fireEvent.change(input, { target: { value: '' } });
    expect(input.value).toBe('');
    expect(onMaxIterationsChange).not.toHaveBeenCalled();

    fireEvent.blur(input);
    expect(input.value).toBe('1');
    expect(onMaxIterationsChange).toHaveBeenCalledWith(1);
  });

  test('Enter key only triggers API call with valid values', async () => {
    const { input, onMaxIterationsChange } = setupMaxIterationsTest();
    
    // Invalid value - should set to 1 and trigger API call
    fireEvent.change(input, { target: { value: '0' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onMaxIterationsChange).toHaveBeenCalledWith(1); // Changed: should be called with corrected value
    
    // Reset mock
    onMaxIterationsChange.mockClear();

    // Valid value
    fireEvent.change(input, { target: { value: '5' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onMaxIterationsChange).toHaveBeenCalledWith(5);
  });
});