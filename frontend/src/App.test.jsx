import React from 'react';
import { BrowserRouter as Router } from 'react-router';
import { render, screen, waitFor, act } from '@testing-library/react';
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
    jest.clearAllMocks();
  });

  test('shows a toast notification on console.error', async () => {
    await act(async () => {
      render(
        <React.StrictMode>
          <Router>
            <App />
          </Router>
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

  test('renders homepage on non-existent route', async () => {
    render(
      <React.StrictMode>
        <Router>
          <App />
        </Router>
      </React.StrictMode>
    );

    // Navigate to a non-existent route
    window.history.pushState({}, 'Test page', '/non-existent-route');

    // Check that the homepage is rendered
    expect(await screen.findByText('New Workflow')).toBeInTheDocument(); 
  });
});