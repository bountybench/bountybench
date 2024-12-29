import { useState, useEffect, useCallback } from 'react';

export const useWorkflowWebSocket = (workflowId) => {
  const [socket, setSocket] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [currentPhase, setCurrentPhase] = useState(null);
  const [currentIteration, setCurrentIteration] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!workflowId) return;

    const ws = new WebSocket(`ws://localhost:8000/ws/${workflowId}`);

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    ws.onclose = () => {
      setIsConnected(false);
      setError('WebSocket connection closed');
    };

    ws.onerror = (event) => {
      setError('WebSocket error occurred');
      console.error('WebSocket error:', event);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case 'initial_state':
          case 'status_update':
            setWorkflowStatus(data.status);
            if (data.current_phase) setCurrentPhase(data.current_phase);
            if (data.current_iteration) setCurrentIteration(data.current_iteration);
            break;
          
          case 'phase_update':
            setCurrentPhase(data.phase);
            break;
          
          case 'iteration_update':
            setCurrentIteration(data.iteration);
            break;
          
          case 'error':
            setError(data.error);
            break;
          
          default:
            console.warn('Unknown message type:', data.type);
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err);
      }
    };

    setSocket(ws);

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [workflowId]);

  const sendMessage = useCallback((message) => {
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(message));
    } else {
      setError('WebSocket is not connected');
    }
  }, [socket]);

  return {
    isConnected,
    workflowStatus,
    currentPhase,
    currentIteration,
    error,
    sendMessage
  };
};
