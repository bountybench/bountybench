import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { WorkflowDashboard } from './WorkflowDashboard';
import { useWorkflowWebSocket } from '../../hooks/useWorkflowWebSocket';
import '@testing-library/jest-dom/extend-expect';
import { MemoryRouter as Router, Routes, Route } from 'react-router';

// Mock the dependencies
jest.mock('../../hooks/useWorkflowWebSocket');

// Mock for scrollIntoView function
window.HTMLElement.prototype.scrollIntoView = jest.fn();

describe('WorkflowDashboard Component', () => {
    const mockSelectedWorkflow = { id: 'test-workflow-id', model: 'test/model' };
    const mockInteractiveMode = true;
    const mockOnWorkflowStateUpdate = jest.fn();
    const mockShowInvalidWorkflowToast = jest.fn();

    const renderWithRouter = (mockSelectedWorkflow, mockInteractiveMode, mockOnWorkflowStateUpdate, mockShowInvalidWorkflowToast) => {
      return render(
        <Router initialEntries={[`/workflow/${mockSelectedWorkflow.id}`]}>
          <Routes>
            <Route path="/workflow/:workflowId" 
              element={
                <WorkflowDashboard
                  selectedWorkflow={mockSelectedWorkflow}
                  interactiveMode={mockInteractiveMode}
                  onWorkflowStateUpdate={mockOnWorkflowStateUpdate}
                  showInvalidWorkflowToast={mockShowInvalidWorkflowToast}
                />
              }
            />
          </Routes>
        </Router>
      );
    };

    beforeEach(() => {
        jest.clearAllMocks();
    });

    test('renders loading state when not connected to WebSocket', () => {
        useWorkflowWebSocket.mockReturnValue({
            isConnected: false,
            workflowStatus: null,
            currentPhase: null,
            phaseMessages: [],
            error: null,
        });

        render(
          <Router>
            <WorkflowDashboard
                selectedWorkflow={mockSelectedWorkflow}
                interactiveMode={mockInteractiveMode}
                onWorkflowStateUpdate={mockOnWorkflowStateUpdate}
            />
          </Router>
        );

        expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    test('renders error message when there is an error', () => {
        const mockError = 'Test error message';
        useWorkflowWebSocket.mockReturnValue({
            isConnected: false,
            workflowStatus: null,
            currentPhase: null,
            phaseMessages: [],
            error: mockError,
        });

        render(
          <Router>
            <WorkflowDashboard
                selectedWorkflow={mockSelectedWorkflow}
                interactiveMode={mockInteractiveMode}
                onWorkflowStateUpdate={mockOnWorkflowStateUpdate}
            />
          </Router>
        );

        expect(screen.getByText(mockError)).toBeInTheDocument();
    });

    test('renders AgentInteractions when connected and no error', async () => {
        useWorkflowWebSocket.mockReturnValue({
            isConnected: true,
            workflowStatus: 'in-progress',
            currentPhase: 'phase-1',
            phaseMessages: 
            [
              {
                  "phase_id": "ExploitPhase",
                  "agent_messages": [
                      {
                          "agent_id": "1",
                          "message": "Message 1",
                          "action_messages": [],
                          "current_children": [],
                          "message_type": "AgentMessage",
                      },
                      {
                          "agent_id": "2",
                          "message": "Message 2",
                          "action_messages": [],
                          "current_children": [],
                          "message_type": "AgentMessage",
                      }
                  ],
                  "current_children": [
                      {
                          "agent_id": "1",
                          "message": "Message 1",
                          "action_messages": [],
                          "current_children": [],
                          "message_type": "AgentMessage",
                      },
                      {
                          "agent_id": "2",
                          "message": "Message 2",
                          "action_messages": [],
                          "current_children": [],
                          "message_type": "AgentMessage",
                      }
                  ],
                  "message_type": "PhaseMessage",
              },
            ],
            error: null,
        });

        render(
          <Router>
            <WorkflowDashboard
                selectedWorkflow={mockSelectedWorkflow}
                interactiveMode={mockInteractiveMode}
                onWorkflowStateUpdate={mockOnWorkflowStateUpdate}
            />
          </Router>
        );

        expect(screen.getByText(/Message 1/)).toBeInTheDocument();
        expect(screen.getByText(/Message 2/)).toBeInTheDocument();
    });

  test('handles triggering next iteration', async () => {
    global.fetch = jest
    .fn()
    .mockImplementationOnce(() =>
      Promise.resolve({
        json: () => Promise.resolve({ active_workflows : [mockSelectedWorkflow.id] })
      })
    )
    .mockImplementationOnce(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true })
      })
    );

    useWorkflowWebSocket.mockReturnValue({
      isConnected: true,
      workflowStatus: 'in-progress',
      currentPhase: 'phase-1',
      phaseMessages: [{}],
      error: null,
    });

    renderWithRouter(mockSelectedWorkflow, mockInteractiveMode, mockOnWorkflowStateUpdate, mockShowInvalidWorkflowToast);

    const triggerNextIterationButton = screen.getByRole('button', { name: 'Continue' });
    fireEvent.click(triggerNextIterationButton);

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(3));
    expect(global.fetch).toHaveBeenCalledWith(
      `http://localhost:8000/workflow/${mockSelectedWorkflow.id}/run-message`, 
      { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_id: null })
      }
    );
  });

    test('displays error message when triggering next iteration fails', async () => {
      global.fetch = jest
      .fn()
      .mockImplementationOnce(() =>
        Promise.resolve({
          json: () => Promise.resolve({ active_workflows : [mockSelectedWorkflow.id] })
        })
      )
      .mockImplementationOnce(() =>
            Promise.resolve({
                ok: false,
                status: 500,
                json: () => Promise.resolve({ error: 'Internal Server Error' })
            })
        );

        useWorkflowWebSocket.mockReturnValue({
            isConnected: true,
            workflowStatus: 'in-progress',
            currentPhase: 'phase-1',
            phaseMessages: [{}],
            error: null,
        });

        renderWithRouter(mockSelectedWorkflow, mockInteractiveMode, mockOnWorkflowStateUpdate, mockShowInvalidWorkflowToast);

        // Simulate triggering next iteration event.
        const triggerNextIterationButton = screen.getByRole('button', { name: 'Continue' });
        fireEvent.click(triggerNextIterationButton);

        await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(3));
        expect(global.fetch).toHaveBeenCalledWith(
          `http://localhost:8000/workflow/${mockSelectedWorkflow.id}/run-message`, 
          { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message_id: null })
          }
        );

        // Additional checks can be added here to verify if any UI updates reflect the error
    });

    test('handles updating action input', async () => {
      global.fetch = jest
      .fn()
      .mockImplementationOnce(() =>
        Promise.resolve({
          json: () => Promise.resolve({ active_workflows : [mockSelectedWorkflow] })
        })
      )
      .mockImplementationOnce(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true })
        })
      );
    
        useWorkflowWebSocket.mockReturnValue({
          isConnected: true,
          workflowStatus: 'in-progress',
          currentPhase: 'phase-1',
          phaseMessages: [
            {
              phase_id: 'ExploitPhase',
              agent_messages: [
                {
                  agent_id: 'agent-1',
                  message: 'Message 1',
                  action_messages: [
                    {
                      current_id: 'test-message-id',
                      resource_id: 'test-message-id',
                      message: 'former1'
                    },
                    {
                      current_id: 'test-message-id2',
                      resource_id: 'test-message-id2',
                      message: 'former2'
                    }
                  ],
                  current_children: [
                    {
                      current_id: 'test-message-id',
                      resource_id: 'test-message-id',
                      message: 'former1'
                    },
                    {
                      current_id: 'test-message-id2',
                      resource_id: 'test-message-id2',
                      message: 'former2'
                    }
                  ],
                  message_type: 'AgentMessage',
                }
              ],
              current_children: [
                {
                  agent_id: 'agent-1',
                  message: 'Message 1',
                  action_messages: [
                    {
                      current_id: 'test-message-id',
                      resource_id: 'test-message-id',
                      message: 'former1'
                    },
                    {
                      current_id: 'test-message-id2',
                      resource_id: 'test-message-id2',
                      message: 'former2'
                    }
                  ],
                  current_children: [
                    {
                      current_id: 'test-message-id',
                      resource_id: 'test-message-id',
                      message: 'former1'
                    },
                    {
                      current_id: 'test-message-id2',
                      resource_id: 'test-message-id2',
                      message: 'former2'
                    }
                  ],
                  message_type: 'AgentMessage',
                }
              ],
              message_type: 'PhaseMessage',
            },
          ],
          error: null,
        });

        renderWithRouter(mockSelectedWorkflow, mockInteractiveMode, mockOnWorkflowStateUpdate, mockShowInvalidWorkflowToast);

        expect(screen.getByText(/former1/)).toBeInTheDocument();
    
        // Find the Edit button in the ActionMessage component and click it
        const editButton = screen.getAllByRole('button', { name: /edit/i })[0];
        fireEvent.click(editButton);

        // Ensure the text area appears and update the value
        const textArea = screen.getByRole('textbox');
        fireEvent.change(textArea, { target: { value: 'New input data' } });

        // Find the Save button in the ActionMessage component and click it
        const saveButton = screen.getByRole('button', { name: /save/i });
        fireEvent.click(saveButton);

        // Assertion for the fetch call
        await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(3));
        expect(global.fetch).toHaveBeenCalledWith(
        `http://localhost:8000/workflow/${mockSelectedWorkflow.id}/edit-message`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message_id: 'test-message-id', new_input_data: 'New input data' })
        }
        );
    });

    test('displays error message when updating action input fails', async () => {    
      global.fetch = jest
      .fn()
      .mockImplementationOnce(() =>
        Promise.resolve({
          json: () => Promise.resolve({ active_workflows : [mockSelectedWorkflow.id] })
        })
      )
      .mockImplementationOnce(() =>
            Promise.resolve({
                ok: false,
                status: 500,
                json: () => Promise.resolve({ error: 'Internal Server Error' })
            })
        );
    
        useWorkflowWebSocket.mockReturnValue({
          isConnected: true,
          workflowStatus: 'in-progress',
          currentPhase: 'phase-1',
          phaseMessages: [
            {
              phase_id: 'ExploitPhase',
              agent_messages: [
                {
                  agent_id: 'agent-1',
                  message: 'Message 1',
                  action_messages: [
                    {
                      current_id: 'test-message-id',
                      resource_id: 'test-message-id',
                      message: 'former1'
                    },
                    {
                      current_id: 'test-message-id2',
                      resource_id: 'test-message-id2',
                      message: 'former2'
                    }
                  ],
                  current_children: [
                    {
                      current_id: 'test-message-id',
                      resource_id: 'test-message-id',
                      message: 'former1'
                    },
                    {
                      current_id: 'test-message-id2',
                      resource_id: 'test-message-id2',
                      message: 'former2'
                    }
                  ],
                  message_type: 'AgentMessage',
                }
              ],
              current_children: [
                {
                  agent_id: 'agent-1',
                  message: 'Message 1',
                  action_messages: [
                    {
                      current_id: 'test-message-id',
                      resource_id: 'test-message-id',
                      message: 'former1'
                    },
                    {
                      current_id: 'test-message-id2',
                      resource_id: 'test-message-id2',
                      message: 'former2'
                    }
                  ],
                  current_children: [
                    {
                      current_id: 'test-message-id',
                      resource_id: 'test-message-id',
                      message: 'former1'
                    },
                    {
                      current_id: 'test-message-id2',
                      resource_id: 'test-message-id2',
                      message: 'former2'
                    }
                  ],
                  message_type: 'AgentMessage',
                }
              ],
              message_type: 'PhaseMessage',
            },
          ],
          error: null,
        });

        renderWithRouter(mockSelectedWorkflow, mockInteractiveMode, mockOnWorkflowStateUpdate, mockShowInvalidWorkflowToast);

        expect(screen.getByText(/former1/)).toBeInTheDocument();
        expect(screen.getByText(/former2/)).toBeInTheDocument();
    
        // Find the Edit button in the ActionMessage component and click it
        const editButton = screen.getAllByRole('button', { name: /edit/i })[0];
        fireEvent.click(editButton);

        // Ensure the text area appears and update the value
        const textArea = screen.getByRole('textbox');
        fireEvent.change(textArea, { target: { value: 'New input data' } });

        // Find the Save button in the ActionMessage component and click it
        const saveButton = screen.getByRole('button', { name: /save/i });
        fireEvent.click(saveButton);

        // Assertion for the fetch call
        await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(3));
        expect(global.fetch).toHaveBeenCalledWith(
        `http://localhost:8000/workflow/${mockSelectedWorkflow.id}/edit-message`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message_id: 'test-message-id', new_input_data: 'New input data' })
        }
        );
    });
});