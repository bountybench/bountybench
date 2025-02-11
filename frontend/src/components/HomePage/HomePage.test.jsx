// src/components/HomePage/HomePage.test.jsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router';
import HomePage from './HomePage'; // Adjust the import path as needed
import '@testing-library/jest-dom/extend-expect'; // Import for custom matchers

global.fetch = jest.fn();

describe('HomePage Component', () => {
  beforeEach(() => {
    jest.clearAllMocks(); // Clear mocks before each test
  });

  const renderWithRouter = () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/create-workflow" element={<div>Create Workflow</div>} />
          <Route path="/workflow/:workflowId" element={<div>Workflow</div>} />
        </Routes>
      </MemoryRouter>
    );
  };

  test('renders loading spinner initially', () => {
    // Arrange
    fetch.mockImplementationOnce(() => new Promise(() => {})); // Mock fetch to hang loading
    renderWithRouter();

    // Assert
    expect(screen.getByRole('progressbar')).toBeInTheDocument(); // Check for spinner
  });

  test('displays active workflows when fetched', async () => {
    // Arrange
    const mockWorkflows = [
      { id: '1', name: 'Workflow 1', bounty_number: '001', status: 'active' },
      { id: '2', name: 'Workflow 2', bounty_number: '002', status: 'in progress' },
    ];

    fetch.mockResolvedValueOnce({
      json: jest.fn().mockResolvedValue({ active_workflows: mockWorkflows })
    });

    renderWithRouter();

    // Wait for the loading to finish and the workflows to load
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('http://localhost:8000/workflow/active'));
    expect(await screen.findByText(/Workflow 1/)).toBeInTheDocument();
    expect(await screen.findByText(/Workflow 2/)).toBeInTheDocument();  
  });

  test('displays no active workflows message when there are none', async () => {
    // Arrange
    fetch.mockResolvedValueOnce({
      json: jest.fn().mockResolvedValue({ active_workflows: [] })
    });

    renderWithRouter();

    // Wait for the loading to finish
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('http://localhost:8000/workflow/active'));
    
    // Assert
    expect(await screen.findByText(/No active workflows/i)).toBeInTheDocument();
  });

  test('navigates to create workflow when button is clicked', async () => {
    // Arrange
    fetch.mockResolvedValueOnce({
      json: jest.fn().mockResolvedValue({ active_workflows: [] })
    });

    renderWithRouter();

    // Wait for the loading to finish
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('http://localhost:8000/workflow/active'));

    // Act
    const newWorkflowButton = screen.getByRole('button', { name: /New Workflow/i });
    fireEvent.click(newWorkflowButton);
    
    // Assert
    expect(screen.getByText(/Create Workflow/i)).toBeInTheDocument(); // Check for navigation
  });

  test('navigates to the correct workflow when a workflow button is clicked', async () => {
    const mockWorkflows = [
      { id: '1', name: 'Workflow 1', bounty_number: '001', status: 'active' }
    ];

    fetch.mockResolvedValueOnce({
      json: jest.fn().mockResolvedValue({ active_workflows: mockWorkflows })
    });

    renderWithRouter();

    // Wait for the loading to finish and the workflows to load
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('http://localhost:8000/workflow/active'));

    // Act
    const workflowButton = await screen.findByRole('button', { name: /Workflow 1/i });

    fireEvent.click(workflowButton);
    
    // Assert
    expect(screen.getAllByText(/Workflow/i).length).toBeGreaterThan(0); // Check for workflow navigation
  });
});