import { useState, useEffect, useCallback, useRef } from 'react';

export const useWorkflowWebSocket = (workflowId) => {
  const [isConnected, setIsConnected] = useState(false);
  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [currentPhase, setCurrentPhase] = useState(null);
  const [currentIteration, setCurrentIteration] = useState(null);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);
  
  const ws = useRef(null);
  const messageIdCounter = useRef(0);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  console.log('useWorkflowWebSocket state:', { 
    workflowId, 
    isConnected, 
    workflowStatus,
    currentPhase,
    currentIteration,
    messageCount: messages.length,
    reconnectAttempts: reconnectAttempts.current
  });

  const connect = useCallback(() => {
    if (!workflowId) return;

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
      console.log('WebSocket connected');
      setIsConnected(true);
      setError(null);
      reconnectAttempts.current = 0;
      
      // Start workflow execution
      try {
        const response = await fetch(`http://localhost:8000/workflow/execute/${workflowId}`, {
          method: 'POST'
        });
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.error || 'Failed to start workflow execution');
        }
        console.log('Workflow execution started');
      } catch (err) {
        console.error('Failed to start workflow:', err);
        setError('Failed to start workflow execution: ' + err.message);
      }
    };

    ws.current.onclose = (event) => {
      console.log('WebSocket disconnected:', event);
      setIsConnected(false);
      
      if (!event.wasClean) {
        reconnectAttempts.current++;
        console.log(`Reconnect attempt ${reconnectAttempts.current}/${maxReconnectAttempts}`);
        // Attempt to reconnect with exponential backoff
        setTimeout(connect, Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000));
      }
    };

    ws.current.onerror = (event) => {
      console.error('WebSocket error:', event);
      setError('Failed to connect to workflow');
    };

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('Received WebSocket message:', data);

        switch (data.type) {
          case 'status_update':
          case 'initial_state':
            console.log('Setting workflow status:', data.status);
            setWorkflowStatus(data.status);
            break;

          case 'phase_update':
            console.log('Setting phase:', data.phase);
            setCurrentPhase(data.phase);
            if (data.phase.status === 'completed') {
              setMessages([]); // Clear messages when phase completes
            }
            break;

          case 'iteration_update':
            console.log('Setting iteration:', data.iteration);
            setCurrentIteration(data.iteration);
            if (data.iteration.input) {
              const message = {
                id: `msg_${messageIdCounter.current++}`,
                content: data.iteration.input.content,
                agent: data.iteration.agent_name,
                timestamp: new Date().toISOString(),
                isUser: false
              };
              setMessages(prev => [...prev, message]);
            }
            if (data.iteration.output) {
              const message = {
                id: `msg_${messageIdCounter.current++}`,
                content: data.iteration.output.content,
                agent: data.iteration.agent_name,
                timestamp: new Date().toISOString(),
                isUser: false
              };
              setMessages(prev => [...prev, message]);
            }
            break;

          case 'action_update':
            console.log('Received action:', data.action);
            const actionMessage = {
              id: `msg_${messageIdCounter.current++}`,
              content: data.action.action_type,
              metadata: data.action.metadata,
              timestamp: data.action.timestamp,
              isUser: false,
              actions: [{
                type: data.action.action_type,
                description: JSON.stringify(data.action.output_data),
                metadata: data.action.metadata
              }]
            };
            setMessages(prev => [...prev, actionMessage]);
            break;

          default:
            console.warn('Unknown message type:', data.type);
        }
      } catch (err) {
        console.error('Error processing WebSocket message:', err);
        setError('Failed to process workflow update: ' + err.message);
      }
    };
  }, [workflowId]);

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

  const sendMessage = useCallback((message) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      console.log('Sending message:', message);
      ws.current.send(JSON.stringify(message));
      
      // Add user message to the list
      const userMessage = {
        id: `msg_${messageIdCounter.current++}`,
        content: message.content,
        timestamp: new Date().toISOString(),
        isUser: true
      };
      setMessages(prev => [...prev, userMessage]);
    } else {
      console.warn('WebSocket not ready for sending');
      setError('Cannot send message: not connected to workflow');
    }
  }, []);

  return {
    isConnected,
    workflowStatus,
    currentPhase,
    currentIteration,
    messages,
    error,
    sendMessage
  };
};
