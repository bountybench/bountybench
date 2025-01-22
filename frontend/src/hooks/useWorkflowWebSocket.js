import { useState, useEffect, useCallback, useRef } from 'react';

export const useWorkflowWebSocket = (workflowId) => {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);
  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [currentPhase, setCurrentPhase] = useState(null);

  const ws = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const handleUpdatedAgentMessage = useCallback((updatedAgentMessage) => {
    setMessages((prevMessages) => {
      const index = prevMessages.findIndex(
        (msg) => msg.current_id === updatedAgentMessage.current_id
      );
      console.log('Updated message:', updatedAgentMessage);

      if (index !== -1) {
        const newMessages = [...prevMessages];
        newMessages[index] = updatedAgentMessage;
        return newMessages;
      } else {
        console.log('Adding as new message');
        return [...prevMessages, updatedAgentMessage];
      }
    });
  }, []);

  const handleWebSocketMessage = useCallback((event) => {
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
          // setMessages((prev) => [...prev, data]);
          setWorkflowStatus(data.workflow_metadata?.workflow_summary || 'Unknown');
          break;

        case 'PhaseMessage':
          setCurrentPhase(data);
          setMessages((prev) => {
            const idx = prev.findIndex((msg) => msg.phase_id === data.phase_id);
            if (idx > -1) {
              const newArr = [...prev];
              newArr[idx] = data;
              return newArr;
            } else {
              return [...prev, data];
            }
          });
          break;

        case 'AgentMessage':
          // handleUpdatedAgentMessage(data);
          break;

        case 'ActionMessage':
          // setMessages((prev) => [...prev, data]);
          break;

        case 'first_message':
          console.log(`Received ${data.message_type}:`, data.content);
          // setMessages((prev) => [...prev, data]);
          break;

        case 'workflow_completed':
          console.log('Workflow completed:', data);
          setWorkflowStatus('completed');
          // setMessages(prev => [...prev, data]);
          break;

        default:
          console.warn('Unknown message_type:', data.message_type);
          // setMessages((prev) => [...prev, data]);
      }
    } catch (err) {
      console.error('Error processing WebSocket message:', err);
      setError('Failed to process workflow update: ' + err.message);
    }
  }, [handleUpdatedAgentMessage]);

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
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('Workflow execution started successfully:', data);
      } catch (err) {
        console.error('Failed to start workflow:', err);
        setError('Failed to start workflow execution: ' + err.message);
      }
    };

    ws.current.onclose = (event) => {
      console.log('WebSocket disconnected for workflow:', workflowId, 'Event:', event);
      setIsConnected(false);

      if (!event.wasClean) {
        reconnectAttempts.current++;
        console.log(`Reconnect attempt ${reconnectAttempts.current}/${maxReconnectAttempts}`);
        setTimeout(connect, Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000));
      }
    };

    ws.current.onerror = (event) => {
      console.error('WebSocket error for workflow:', workflowId, 'Event:', event);
      setError('WebSocket error: ' + (event.message || 'Unknown error'));
    };

    ws.current.onmessage = handleWebSocketMessage;
  }, [workflowId, handleWebSocketMessage]);

  useEffect(() => {
    if (workflowId) {
      connect();
      return () => {
        if (ws.current) {
          console.log('Closing WebSocket connection');
          ws.current.close();
          ws.current = null;
        }
      };
    }
  }, [connect, workflowId]);

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

  useEffect(() => {
    console.log('Connection status:', isConnected);
  }, [isConnected]);

  useEffect(() => {
    console.log('Workflow status changed:', workflowStatus);
  }, [workflowStatus]);

  useEffect(() => {
    if (messages.length > 0) {
      console.log('Last message:', messages[messages.length - 1]);
    }
  }, [messages]);

  return {
    isConnected,
    messages,
    error,
    workflowStatus,
    currentPhase,
    sendMessage
  };
};