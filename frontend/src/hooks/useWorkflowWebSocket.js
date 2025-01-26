import { useState, useEffect, useCallback, useRef } from 'react';

export const useWorkflowWebSocket = (workflowId) => {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);
  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [currentPhase, setCurrentPhase] = useState(null);
  const [isReconnecting, setIsReconnecting] = useState(false);

  const ws = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectTimeoutRef = useRef(null);
  const workflowExecuted = useRef(false);

  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

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
          setMessages((prev) => [...prev, data]);
          setWorkflowStatus(data.workflow_metadata?.workflow_summary || 'Unknown');
          break;

        case 'PhaseMessage':
          setCurrentPhase(data);
          setMessages((prev) => {
            const idx = prev.findIndex((msg) => msg.current_id === data.current_id);
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
          handleUpdatedAgentMessage(data);
          break;

        case 'ActionMessage':
          setMessages((prev) => [...prev, data]);
          break;

        case 'first_message':
          console.log(`Received ${data.message_type}:`, data.content);
          setMessages((prev) => [...prev, data]);
          break;

        case 'workflow_completed':
          console.log('Workflow completed:', data);
          setWorkflowStatus('completed');
          setMessages(prev => [...prev, data]);
          break;

        case 'heartbeat':
          // Silently handle heartbeat
          break;

        default:
          console.warn('Unknown message_type:', data.message_type);
          setMessages((prev) => [...prev, data]);
      }
    } catch (err) {
      console.error('Error processing WebSocket message:', err);
      setError('Failed to process workflow update: ' + err.message);
    }
  }, [handleUpdatedAgentMessage]);

  const executeWorkflow = useCallback(async () => {
    if (workflowExecuted.current) {
      return;
    }
    
    try {
      const response = await fetch(`http://localhost:8000/workflow/execute/${workflowId}`, {
        method: 'POST'
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('Workflow execution started successfully:', data);
      workflowExecuted.current = true;
    } catch (err) {
      console.error('Failed to start workflow:', err);
      setError('Failed to start workflow execution: ' + err.message);
      throw err;
    }
  }, [workflowId]);

  const connect = useCallback(async () => {
    if (!workflowId) {
      console.warn('No workflow ID provided, skipping connection');
      return;
    }

    if (reconnectAttempts.current >= maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      setError('Failed to connect after multiple attempts');
      setIsReconnecting(false);
      return;
    }

    // Clear any existing connection
    if (ws.current) {
      try {
        ws.current.close();
      } catch (err) {
        console.warn('Error closing existing connection:', err);
      }
      ws.current = null;
    }

    const wsUrl = `ws://localhost:8000/ws/${workflowId}`;
    console.log('Connecting to WebSocket:', wsUrl);

    try {
      ws.current = new WebSocket(wsUrl);
      let connectionTimeout = setTimeout(() => {
        if (ws.current && ws.current.readyState !== WebSocket.OPEN) {
          console.warn('WebSocket connection timeout');
          ws.current.close();
        }
      }, 5000); // 5 second connection timeout

      ws.current.onopen = async () => {
        clearTimeout(connectionTimeout);
        console.log('WebSocket connected for workflow:', workflowId);
        setIsConnected(true);
        setError(null);
        setIsReconnecting(false);
        reconnectAttempts.current = 0;
        clearReconnectTimeout();

        // Only execute workflow if this is the first connection
        if (!workflowExecuted.current) {
          try {
            await executeWorkflow();
          } catch (err) {
            // Error already handled in executeWorkflow
          }
        }
      };

      ws.current.onclose = (event) => {
        clearTimeout(connectionTimeout);
        console.log('WebSocket disconnected for workflow:', workflowId, 'Event:', event);
        setIsConnected(false);
        ws.current = null;

        // Only attempt reconnect if not a clean close and not shutting down
        if (!event.wasClean && !isReconnecting && !workflowExecuted.current) {
          setIsReconnecting(true);
          reconnectAttempts.current++;
          console.log(`Reconnect attempt ${reconnectAttempts.current}/${maxReconnectAttempts}`);
          
          // Exponential backoff with max delay of 10 seconds
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000);
          reconnectTimeoutRef.current = setTimeout(() => connect(), delay);
        }
      };

      ws.current.onerror = (event) => {
        console.error('WebSocket error for workflow:', workflowId, 'Event:', event);
        setError('WebSocket error: ' + (event.message || 'Unknown error'));
        // Don't set ws.current to null here, let onclose handle it
      };

      ws.current.onmessage = handleWebSocketMessage;
    } catch (err) {
      console.error('Error creating WebSocket:', err);
      setError('Failed to create WebSocket connection: ' + err.message);
      
      if (!isReconnecting) {
        setIsReconnecting(true);
        reconnectAttempts.current++;
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000);
        reconnectTimeoutRef.current = setTimeout(() => connect(), delay);
      }
    }
  }, [workflowId, handleWebSocketMessage, clearReconnectTimeout, executeWorkflow, isReconnecting]);

  useEffect(() => {
    if (workflowId) {
      connect();
      return () => {
        clearReconnectTimeout();
        if (ws.current) {
          console.log('Closing WebSocket connection');
          ws.current.close();
          ws.current = null;
        }
        workflowExecuted.current = false;
      };
    }
  }, [workflowId, connect, clearReconnectTimeout]);

  const sendMessage = useCallback((message) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
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
    sendMessage,
    isReconnecting
  };
};