import { useState, useEffect, useCallback, useRef } from 'react';

export const useWorkflowWebSocket = (workflowId) => {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);

  // If you still want to track these separately:
  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [currentPhase, setCurrentPhase] = useState(null);

  const ws = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  // ----------------------------------
  // 1) Connect / Reconnect logic
  // ----------------------------------
  const connect = useCallback(() => {
    if (!workflowId) {
      console.warn('No workflow ID provided, skipping connection');
      return;
    }

    if (reconnectAttempts.current >= maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      setError('Failed to connect after multiple attempts');
      return;
    }

    const wsUrl = `ws://localhost:8000/ws/${workflowId}`;
    console.log('Connecting to WebSocket:', wsUrl);

    if (ws.current?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    ws.current = new WebSocket(wsUrl);

    // WebSocket open handler
    ws.current.onopen = async () => {
      console.log('WebSocket connected for workflow:', workflowId);
      setIsConnected(true);
      setError(null);
      reconnectAttempts.current = 0;

      try {
        const response = await fetch(`http://localhost:8000/workflow/execute/${workflowId}`, {
          method: 'POST'
        });
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.error || 'Failed to start workflow execution');
        }
        console.log('Workflow execution started successfully');
      } catch (err) {
        console.error('Failed to start workflow:', err);
        setError('Failed to start workflow execution: ' + err.message);
      }
    };

    // WebSocket close handler
    ws.current.onclose = (event) => {
      console.log('WebSocket disconnected for workflow:', workflowId, 'Event:', event);
      setIsConnected(false);

      if (!event.wasClean) {
        reconnectAttempts.current++;
        console.log(`Reconnect attempt ${reconnectAttempts.current}/${maxReconnectAttempts}`);
        setTimeout(connect, Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000));
      }
    };

    // WebSocket error handler
    ws.current.onerror = (event) => {
      console.error('WebSocket error for workflow:', workflowId, 'Event:', event);
      setError('Failed to connect to workflow');
    };

    // ----------------------------------
    // 2) onmessage: handle real-time updates
    // We assume that we will only receive phase messages (where we obtain Agent > Action messages)
    // Or workflow messages (where we only retrieve workflow status)
    // ----------------------------------
    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('Raw WebSocket message:', event.data);
        console.log('Parsed WebSocket "message_type":', data.message_type);
        console.log('Full message data:', data);

        switch (data.message_type) {
          case 'status_update':
          case 'initial_state':
            console.log('Handling status update:', data.status);
            setWorkflowStatus(data.status);
            break;

          case 'WorkflowMessage':
            setWorkflowStatus(data.workflow_metadata?.workflow_summary || 'Unknown');
            break;

          case 'PhaseMessage':
            setCurrentPhase(data);

            setMessages((prev) => {
              const idx = prev.findIndex((msg) => msg.current_id === data.current_id);
              if (idx > -1) {
                // Replaces old stored phase message for new version
                const newArr = [...prev];
                newArr[idx] = data;
                return newArr;
              } else {
                // Or appends new phase
                return [...prev, data];
              }
            });
            break;

          default:
            console.warn('Unknown message_type:', data.message_type);
            setMessages((prev) => [...prev, data]);
        }
      } catch (err) {
        console.error('Error processing WebSocket message:', err);
        setError('Failed to process workflow update: ' + err.message);
      }
    };
  }, [workflowId]);

  // ----------------------------------
  // 3) useEffect to initiate connection
  // ----------------------------------
  useEffect(() => {
    if (workflowId) {
      connect();
      return () => {
        if (ws.current) {
          console.log('Closing WebSocket connection');
          ws.current.close();
        }
      };
    }
  }, [connect, workflowId]);

  // ----------------------------------
  // 4) sendMessage: for user messages (optional)
  // ----------------------------------
  const sendMessage = useCallback((message) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      console.log('Sending user message:', message);
      ws.current.send(
        JSON.stringify({
          message_type: 'user_message',
          content: message.content
        })
      );
    } else {
      console.warn('WebSocket not ready for sending');
      setError('Cannot send message: not connected to workflow');
    }
  }, []);

  // ----------------------------------
  // 5) Return relevant state/hooks
  // ----------------------------------
  return {
    isConnected,
    messages,
    error,
    workflowStatus,
    currentPhase,
    sendMessage
  };
};