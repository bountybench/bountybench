import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import App from './App';
import '@testing-library/jest-dom/extend-expect';
import { useServerAvailability } from './hooks/useServerAvailability';

jest.mock('./hooks/useServerAvailability');

// Mock the fetch function globally
global.fetch = jest.fn();

describe('App Component', () => {
  const originalConsoleError = console.error;

  beforeEach(() => {
    jest.clearAllMocks();

    useServerAvailability.mockReturnValue({
      isServerAvailable: true,
      isChecking: false
    });

    console.error = jest.fn((...args) => {
        const toastError = require('react-toastify').toast.error;
        toastError(args.join(' '));
        originalConsoleError(...args);
      });
  });

  afterEach(() => {
    console.error = originalConsoleError;
  });

  test('shows a toast notification on console.error', async () => {
    await act(async () => {
        render(
          <React.StrictMode>
              <App />
          </React.StrictMode>
        );
  
        // Triggering a console error message
        console.error('Test error message');
      });
    
    await waitFor(() => {
      const toasts = screen.getAllByText('Test error message');
      expect(toasts.length).toBeGreaterThan(0);
      expect(toasts[0]).toBeInTheDocument();
    });
  });

  test('shows a proper toast notification when fetch fails', async () => {
    await act(async () => {
        render(
          <React.StrictMode>
              <App />
          </React.StrictMode>
        );
    });

    const startWorkflowButton = await screen.findByText(/Start Workflow/i);
    await act(async () => {
        // Trigger the start workflow button click
        fireEvent.click(startWorkflowButton);
    });

    await waitFor(() => {
      const toasts = screen.getAllByText(/Failed to get response from server/i);
      expect(toasts.length).toBeGreaterThan(0);
      expect(toasts[0]).toBeInTheDocument();
    });
  });
});